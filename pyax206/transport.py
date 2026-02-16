from __future__ import annotations
import time
import struct
from dataclasses import dataclass

import usb.core
import usb.util

from .constants import DEFAULT_INTF, DEFAULT_EP_IN, DEFAULT_EP_OUT, CB16_INIT, CB16_FRAME
from .errors import AX206NotFoundError, AX206USBError, AX206ProtocolError

@dataclass
class USBConfig:
    vid: int
    pid: int
    intf: int = DEFAULT_INTF
    ep_out: int = DEFAULT_EP_OUT
    ep_in: int = DEFAULT_EP_IN

class AX206Transport:
    """Low-level AX206 USB transport (CBW/CSW)."""

    def __init__(self, cfg: USBConfig, *, chunk_size: int = 16384, tag: int = 0xDEADBEEF, auto_reconnect: bool = True):
        self.cfg = cfg
        self.chunk_size = int(chunk_size)
        self.tag = int(tag) & 0xFFFFFFFF
        self.auto_reconnect = bool(auto_reconnect)
        self.dev = None

    def open(self) -> None:
        try:
            dev = usb.core.find(idVendor=self.cfg.vid, idProduct=self.cfg.pid)
        except Exception as e:
            raise AX206USBError(str(e)) from e
        if dev is None:
            raise AX206NotFoundError(f"AX206 device not found (VID={self.cfg.vid:#06x} PID={self.cfg.pid:#06x}).")
        try:
            dev.set_configuration()
            usb.util.claim_interface(dev, self.cfg.intf)
        except usb.core.USBError as e:
            raise AX206USBError(f"Could not claim interface {self.cfg.intf}: {e}") from e
        self.dev = dev

    def close(self) -> None:
        if self.dev is None:
            return
        try:
            try:
                usb.util.release_interface(self.dev, self.cfg.intf)
            except Exception:
                pass
            usb.util.dispose_resources(self.dev)
        finally:
            self.dev = None

    def reconnect(self, timeout_s: float = 10.0) -> None:
        self.close()
        end = time.time() + timeout_s
        last = None
        while time.time() < end:
            try:
                self.open()
                return
            except Exception as e:
                last = e
                time.sleep(0.25)
        raise AX206NotFoundError(f"Could not reconnect device within {timeout_s}s. Last error: {last}")

    @staticmethod
    def _make_cbw(tag_u32: int, transfer_len: int, cb16: bytes) -> bytes:
        return (
            b"USBC"
            + struct.pack("<I", tag_u32)
            + struct.pack("<I", transfer_len)
            + b"\x00"
            + b"\x00"
            + b"\x10"
            + cb16
        )

    def _read_csw(self, expected_tag: int, timeout_s: float = 3.0) -> int:
        if self.dev is None:
            raise AX206USBError("Device not open")
        expected = struct.pack("<I", expected_tag & 0xFFFFFFFF)
        end = time.time() + timeout_s
        while time.time() < end:
            try:
                pkt = bytes(self.dev.read(self.cfg.ep_in, 64, timeout=500))
            except usb.core.USBError:
                continue
            i = pkt.find(b"USBS")
            if i != -1 and len(pkt) >= i + 13 and pkt[i+4:i+8] == expected:
                return pkt[i+12]
        raise AX206ProtocolError("Timed out waiting for CSW (USBS)")

    def _write_all(self, data: bytes, timeout: int = 8000) -> None:
        if self.dev is None:
            raise AX206USBError("Device not open")
        for i in range(0, len(data), self.chunk_size):
            self.dev.write(self.cfg.ep_out, data[i:i+self.chunk_size], timeout=timeout)

    def init(self) -> None:
        try:
            self.dev.write(self.cfg.ep_out, self._make_cbw(self.tag, 5, CB16_INIT), timeout=3000)
            st = self._read_csw(self.tag, timeout_s=3.0)
        except usb.core.USBError as e:
            if self.auto_reconnect:
                self.reconnect()
                self.dev.write(self.cfg.ep_out, self._make_cbw(self.tag, 5, CB16_INIT), timeout=3000)
                st = self._read_csw(self.tag, timeout_s=3.0)
            else:
                raise AX206USBError(str(e)) from e
        if st != 0:
            raise AX206ProtocolError(f"INIT failed (CSW status={st})")

    def send_frame(self, frame_bytes: bytes, *, timeout_s: float = 5.0) -> None:
        if self.dev is None:
            raise AX206USBError("Device not open")
        n = len(frame_bytes)
        try:
            self.dev.write(self.cfg.ep_out, self._make_cbw(self.tag, n, CB16_FRAME), timeout=3000)
            if n >= 262144:
                self._write_all(frame_bytes[:262144])
                self._write_all(frame_bytes[262144:])
            else:
                self._write_all(frame_bytes)
            st = self._read_csw(self.tag, timeout_s=timeout_s)
        except usb.core.USBError as e:
            if self.auto_reconnect:
                self.reconnect()
                self.init()
                self.dev.write(self.cfg.ep_out, self._make_cbw(self.tag, n, CB16_FRAME), timeout=3000)
                if n >= 262144:
                    self._write_all(frame_bytes[:262144])
                    self._write_all(frame_bytes[262144:])
                else:
                    self._write_all(frame_bytes)
                st = self._read_csw(self.tag, timeout_s=timeout_s)
            else:
                raise AX206USBError(str(e)) from e
        if st != 0:
            raise AX206ProtocolError(f"FRAME failed (CSW status={st})")
