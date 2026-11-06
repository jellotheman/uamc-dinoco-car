"""Single-session serial worker with bounded writes and no command replay."""
import threading
import time

from .serial_protocol import encode_command


class SerialTransport:
    def __init__(self, device, baud, handshake_timeout, write_timeout, neutral, factory=None, clock=time.monotonic):
        if factory is None:
            import serial
            factory = serial.Serial
        self.device, self.baud = device, baud
        self.handshake_timeout, self.write_timeout = handshake_timeout, write_timeout
        self.neutral = encode_command(*neutral)
        self.factory, self.clock = factory, clock
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.closed = False
        self.ready = False
        self.connected_at = None
        self.error = 'Serial link starting'
        self.pending = None
        self.generation = 0
        self.neutral_ack = -1
        self.serial = None
        self.thread = threading.Thread(target=self._run, daemon=True, name='vehicle-serial')
        self.thread.start()

    def submit(self, pair, deadline):
        packet = encode_command(*pair)
        with self.lock:
            if not self.ready or self.closed:
                return False
            self.pending = (packet, deadline, self.generation)
        self.wake.set()
        return True

    def neutral_confirmed(self):
        with self.lock:
            return self.ready and self.neutral_ack == self.generation

    def invalidate(self):
        with self.lock:
            self.generation += 1
            self.pending = (self.neutral, self.clock() + self.write_timeout, self.generation) if self.ready and not self.closed else None
        self.wake.set()

    def _write(self, packet):
        count = self.serial.write(packet)
        if count != len(packet):
            raise OSError('short serial write')

    def _run(self):
        try:
            port = self.factory(port=self.device, baudrate=self.baud, timeout=min(0.05, self.handshake_timeout),
                                write_timeout=self.write_timeout, exclusive=True)
            self.serial = port
            deadline = self.clock() + self.handshake_timeout
            line = bytearray()
            while not self.closed and self.clock() < deadline:
                chunk = port.read(1)
                if not chunk:
                    continue
                line.extend(chunk)
                if len(line) > 128:
                    raise OSError('oversized handshake')
                if chunk == b'\n':
                    if bytes(line).strip(b'\r\n') != b'READY':
                        raise OSError('invalid handshake')
                    break
            else:
                raise OSError('handshake timeout or shutdown')
            if self.closed or self.clock() >= deadline:
                raise OSError('handshake timeout or shutdown')
            self._write(self.neutral)
            with self.lock:
                if self.closed:
                    return
                self.ready = True
                self.connected_at = self.clock()
                self.error = ''
            while not self.closed:
                self.wake.wait(0.05)
                self.wake.clear()
                with self.lock:
                    item, self.pending = self.pending, None
                if item is None:
                    continue
                packet, until, generation = item
                with self.lock:
                    valid = not self.closed and generation == self.generation and self.clock() <= until
                # A valid item is committed under the lock; invalidation can
                # queue neutral while this one bounded write is in flight.
                if valid:
                    self._write(packet)
                    if packet == self.neutral:
                        with self.lock:
                            if generation == self.generation:
                                self.neutral_ack = generation
        except Exception as exc:
            with self.lock:
                self.error = 'Serial link unavailable: ' + str(exc)
        finally:
            with self.lock:
                self.ready = False
                self.pending = None
                self.generation += 1
            if self.serial is not None:
                try:
                    self.serial.close()
                except Exception:
                    pass

    def close(self):
        self.invalidate()
        # Permit the neutral attempt one write timeout, then cancel any I/O.
        self.wake.set()
        self.thread.join(self.write_timeout + 0.05)
        self.closed = True
        self.wake.set()
        port = self.serial
        if port is not None:
            def cancel_and_close():
                for name in ('cancel_read', 'cancel_write', 'close'):
                    try:
                        method = getattr(port, name, None)
                        if method is not None:
                            method()
                    except Exception:
                        pass
            closer = threading.Thread(target=cancel_and_close, daemon=True)
            closer.start()
            closer.join(0.1)
        self.thread.join(0.2)
