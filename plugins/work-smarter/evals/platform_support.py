import errno
import os
import signal
import subprocess
import time


IS_WINDOWS = os.name == 'nt'


def acquire_lock(handle):
    if not IS_WINDOWS:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return
    import msvcrt
    # Lock a common byte even when the lock file is empty. Never unlink it:
    # replacing the inode would allow a second owner to bypass existing waiters.
    while True:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EDEADLK):
                raise
            time.sleep(0.05)


def release_lock(handle):
    if IS_WINDOWS:
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    TH32CS_SNAPTHREAD = 0x00000004
    THREAD_SUSPEND_RESUME = 0x0002
    CREATE_SUSPENDED = 0x00000004

    class _BasicLimits(ctypes.Structure):
        _fields_ = [
            ('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
            ('flags', wintypes.DWORD), ('min_working_set', ctypes.c_size_t),
            ('max_working_set', ctypes.c_size_t), ('active_processes', wintypes.DWORD),
            ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
            ('scheduling', wintypes.DWORD),
        ]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ('basic', _BasicLimits), ('io', ctypes.c_uint64 * 6),
            ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
            ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t),
        ]

    class _ThreadEntry(ctypes.Structure):
        _fields_ = [
            ('size', wintypes.DWORD), ('usage', wintypes.DWORD),
            ('thread_id', wintypes.DWORD), ('process_id', wintypes.DWORD),
            ('base_priority', wintypes.LONG), ('delta_priority', wintypes.LONG),
            ('flags', wintypes.DWORD),
        ]

    _kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    for _name, _args, _result in (
        ('CreateJobObjectW', [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        ('SetInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        ('AssignProcessToJobObject', [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        ('TerminateJobObject', [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
        ('CreateToolhelp32Snapshot', [wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE),
        ('Thread32First', [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)], wintypes.BOOL),
        ('Thread32Next', [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)], wintypes.BOOL),
        ('OpenThread', [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        ('ResumeThread', [wintypes.HANDLE], wintypes.DWORD),
    ):
        _function = getattr(_kernel, _name)
        _function.argtypes, _function.restype = _args, _result

    def _checked(value):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    class _WindowsJob:
        def __init__(self):
            self.handle = _checked(_kernel.CreateJobObjectW(None, None))
            try:
                limits = _ExtendedLimits()
                limits.basic.flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                _checked(_kernel.SetInformationJobObject(
                    self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
            except BaseException:
                self.close()
                raise

        def assign_and_resume(self, process):
            _checked(_kernel.AssignProcessToJobObject(self.handle, int(process._handle)))
            # Popen closes the primary thread handle. The child is still suspended,
            # so it has exactly one thread; reopen it before allowing any code to run.
            snapshot = _kernel.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
            if snapshot == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                entry = _ThreadEntry()
                entry.size = ctypes.sizeof(entry)
                found = _kernel.Thread32First(snapshot, ctypes.byref(entry))
                while found:
                    if entry.process_id == process.pid:
                        thread = _checked(_kernel.OpenThread(THREAD_SUSPEND_RESUME, False, entry.thread_id))
                        try:
                            previous = _kernel.ResumeThread(thread)
                            if previous == 0xFFFFFFFF:
                                raise ctypes.WinError(ctypes.get_last_error())
                            if previous != 1:
                                raise OSError('primary thread was not suspended exactly once')
                            return
                        finally:
                            _kernel.CloseHandle(thread)
                    found = _kernel.Thread32Next(snapshot, ctypes.byref(entry))
                raise OSError('suspended process primary thread was not found')
            finally:
                _kernel.CloseHandle(snapshot)

        def terminate(self):
            _checked(_kernel.TerminateJobObject(self.handle, 1))

        def close(self):
            if self.handle is not None:
                _checked(_kernel.CloseHandle(self.handle))
                self.handle = None


def start_process(command, **kwargs):
    """Start in an owned POSIX session or a Windows kill-on-close job."""
    if not IS_WINDOWS:
        return subprocess.Popen(command, start_new_session=True, **kwargs)
    job = _WindowsJob()
    process = None
    try:
        flags = CREATE_SUSPENDED | subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(command, creationflags=flags, **kwargs)
        process._evaluation_job = job
        job.assign_and_resume(process)
        return process
    except BaseException:
        try:
            if process is not None:
                process.kill()
                process.wait()
        finally:
            job.close()
        raise


def close_process(process):
    """Release job ownership, also killing descendants after a normal parent exit."""
    job = getattr(process, '_evaluation_job', None)
    if job is not None:
        job.close()
        process._evaluation_job = None


def terminate_process_group(process):
    try:
        if IS_WINDOWS:
            process._evaluation_job.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            return process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if IS_WINDOWS:
                process._evaluation_job.terminate()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            return process.communicate()
    finally:
        close_process(process)


def atomic_replace(source, destination):
    """Retry transient Windows sharing violations without replacing atomic rename."""
    for attempt in range(20):
        try:
            source.replace(destination)
            return
        except OSError as error:
            if not IS_WINDOWS or getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == 19:
                raise
            time.sleep(0.05)
