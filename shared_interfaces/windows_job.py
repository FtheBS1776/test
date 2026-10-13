"""Minimal Windows Job Object support for a fixture-only containment probe.

This module is deliberately not a general sandbox.  It exposes only the
small Job Object operations needed by the Phase 2B2B deterministic test.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import time


JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS = 1
JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS = 3
SYNCHRONIZE = 0x00100000
PROCESS_QUERY_LIMITED_INFORMATION = 0x00001000
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
STILL_ACTIVE = 259


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


def _require_windows():
    if os.name != "nt":
        raise OSError("Windows Job Objects require Windows")


def _kernel32():
    _require_windows()
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    library.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    library.CreateJobObjectW.restype = wintypes.HANDLE
    library.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    library.SetInformationJobObject.restype = wintypes.BOOL
    library.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD))
    library.QueryInformationJobObject.restype = wintypes.BOOL
    library.AssignProcessToJobObject.argtypes = (
        wintypes.HANDLE, wintypes.HANDLE)
    library.AssignProcessToJobObject.restype = wintypes.BOOL
    library.IsProcessInJob.argtypes = (
        wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL))
    library.IsProcessInJob.restype = wintypes.BOOL
    library.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    library.TerminateJobObject.restype = wintypes.BOOL
    library.OpenProcess.argtypes = (
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    library.OpenProcess.restype = wintypes.HANDLE
    library.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    library.WaitForSingleObject.restype = wintypes.DWORD
    library.GetExitCodeProcess.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    library.GetExitCodeProcess.restype = wintypes.BOOL
    library.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD))
    library.QueryFullProcessImageNameW.restype = wintypes.BOOL
    library.CloseHandle.argtypes = (wintypes.HANDLE,)
    library.CloseHandle.restype = wintypes.BOOL
    return library


def _winerror(operation):
    code = ctypes.get_last_error()
    raise OSError(code, f"{operation} failed", None, code)


def _check_structure_layout():
    pointer_size = ctypes.sizeof(ctypes.c_void_p)
    if pointer_size == 8:
        expected = (64, 48, 144, 48)
    elif pointer_size == 4:
        expected = (48, 48, 112, 48)
    else:
        raise RuntimeError("unsupported pointer width")
    observed = (
        ctypes.sizeof(_JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ctypes.sizeof(_IO_COUNTERS),
        ctypes.sizeof(_JOBOBJECT_EXTENDED_LIMIT_INFORMATION),
        ctypes.sizeof(_JOBOBJECT_BASIC_ACCOUNTING_INFORMATION),
    )
    if observed != expected:
        raise RuntimeError("unexpected Windows Job Object structure layout")
    return observed


class ProcessWaitHandle:
    """Owned process handle used for PID-reuse-safe bounded waits."""

    __slots__ = ("_handle",)

    def __init__(self, pid):
        if type(pid) is not int or pid <= 0:
            raise ValueError("invalid process id")
        library = _kernel32()
        handle = library.OpenProcess(
            SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            _winerror("OpenProcess")
        self._handle = int(handle)

    @property
    def handle(self):
        if not self._handle:
            raise RuntimeError("process handle is closed")
        return self._handle

    def wait(self, timeout_seconds):
        if (type(timeout_seconds) not in (int, float)
                or timeout_seconds < 0 or timeout_seconds > 60):
            raise ValueError("invalid wait timeout")
        milliseconds = min(0xFFFFFFFE, int(timeout_seconds * 1000))
        result = _kernel32().WaitForSingleObject(self.handle, milliseconds)
        if result == WAIT_OBJECT_0:
            return True
        if result == WAIT_TIMEOUT:
            return False
        if result == WAIT_FAILED:
            _winerror("WaitForSingleObject")
        raise OSError("unexpected wait result")

    def exit_code(self):
        value = wintypes.DWORD()
        if not _kernel32().GetExitCodeProcess(
                self.handle, ctypes.byref(value)):
            _winerror("GetExitCodeProcess")
        return int(value.value)

    def image_path(self):
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not _kernel32().QueryFullProcessImageNameW(
                self.handle, 0, buffer, ctypes.byref(size)):
            _winerror("QueryFullProcessImageNameW")
        return buffer.value

    def close(self):
        handle, self._handle = self._handle, 0
        if handle and not _kernel32().CloseHandle(handle):
            _winerror("CloseHandle(process)")

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()

    def __del__(self):
        handle, self._handle = getattr(self, "_handle", 0), 0
        if handle:
            try:
                _kernel32().CloseHandle(handle)
            except Exception:
                pass


class WindowsJob:
    """One unnamed, non-breakaway, kill-on-close Windows Job Object."""

    __slots__ = ("_handle",)

    def __init__(self):
        _check_structure_layout()
        library = _kernel32()
        handle = library.CreateJobObjectW(None, None)
        if not handle:
            _winerror("CreateJobObjectW")
        self._handle = int(handle)
        try:
            information = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            information.BasicLimitInformation.LimitFlags = (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
            if not library.SetInformationJobObject(
                    self.handle, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                    ctypes.byref(information), ctypes.sizeof(information)):
                _winerror("SetInformationJobObject")
            if self.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
                raise RuntimeError("job limit verification failed")
        except BaseException:
            try:
                self.close()
            except Exception:
                pass
            raise

    @property
    def handle(self):
        if not self._handle:
            raise RuntimeError("job handle is closed")
        return self._handle

    def _query(self, information_class, structure):
        returned = wintypes.DWORD()
        if not _kernel32().QueryInformationJobObject(
                self.handle, information_class, ctypes.byref(structure),
                ctypes.sizeof(structure), ctypes.byref(returned)):
            _winerror("QueryInformationJobObject")
        if returned.value not in (0, ctypes.sizeof(structure)):
            raise RuntimeError("unexpected job query size")
        return structure

    def limit_flags(self):
        information = self._query(
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            _JOBOBJECT_EXTENDED_LIMIT_INFORMATION())
        return int(information.BasicLimitInformation.LimitFlags)

    def accounting(self):
        value = self._query(
            JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS,
            _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION())
        return {
            "total_processes": int(value.TotalProcesses),
            "active_processes": int(value.ActiveProcesses),
            "terminated_processes": int(value.TotalTerminatedProcesses),
        }

    def process_ids(self):
        buffer = ctypes.create_string_buffer(65536)
        returned = wintypes.DWORD()
        if not _kernel32().QueryInformationJobObject(
                self.handle, JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS,
                buffer, ctypes.sizeof(buffer), ctypes.byref(returned)):
            _winerror("QueryInformationJobObject(process ids)")
        counts = (wintypes.DWORD * 2).from_buffer_copy(buffer.raw[:8])
        assigned, listed = int(counts[0]), int(counts[1])
        if assigned != listed or listed > 1024:
            raise RuntimeError("incomplete job process-id list")
        item_size = ctypes.sizeof(ctypes.c_size_t)
        needed = 8 + listed * item_size
        if needed > len(buffer):
            raise RuntimeError("invalid job process-id list size")
        values = (ctypes.c_size_t * listed).from_buffer_copy(
            buffer.raw[8:needed])
        return tuple(int(value) for value in values)

    def assign_handle(self, process_handle):
        if type(process_handle) is not int or process_handle <= 0:
            raise ValueError("invalid process handle")
        if not _kernel32().AssignProcessToJobObject(
                self.handle, process_handle):
            _winerror("AssignProcessToJobObject")
        if not self.contains_handle(process_handle):
            raise RuntimeError("job membership verification failed")

    def assign_process(self, process):
        self.assign_handle(int(process._handle))

    def contains_handle(self, process_handle):
        result = wintypes.BOOL()
        if not _kernel32().IsProcessInJob(
                process_handle, self.handle, ctypes.byref(result)):
            _winerror("IsProcessInJob")
        return bool(result.value)

    def wait_for_active(self, expected, timeout_seconds):
        if type(expected) is not int or expected < 0:
            raise ValueError("invalid active-process expectation")
        deadline = time.monotonic() + timeout_seconds
        while True:
            observed = self.accounting()["active_processes"]
            if observed == expected:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)

    def terminate(self, exit_code):
        if type(exit_code) is not int or not 0 <= exit_code <= 0xFFFFFFFF:
            raise ValueError("invalid exit code")
        if not _kernel32().TerminateJobObject(self.handle, exit_code):
            _winerror("TerminateJobObject")

    def close(self):
        handle, self._handle = self._handle, 0
        if handle and not _kernel32().CloseHandle(handle):
            _winerror("CloseHandle(job)")

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()

    def __del__(self):
        handle, self._handle = getattr(self, "_handle", 0), 0
        if handle:
            try:
                _kernel32().CloseHandle(handle)
            except Exception:
                pass


__all__ = [
    "JOB_OBJECT_LIMIT_BREAKAWAY_OK",
    "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
    "JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK",
    "ProcessWaitHandle",
    "STILL_ACTIVE",
    "WindowsJob",
]
