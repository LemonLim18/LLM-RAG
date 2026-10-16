"""Bound extraction child processes without invoking a shell or inheriting secrets."""
import os
import subprocess


def bounded_process(command, input_text, timeout=30, memory_mb=768):
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','PATHEXT'}}
    job=None
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,encoding='utf-8',env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    try:
        if os.name=='nt':
            # The child blocks on stdin until the memory/job boundary is installed.
            import ctypes
            from ctypes import wintypes
            class Basic(ctypes.Structure):
                _fields_=[('ProcessTime',ctypes.c_int64),('JobTime',ctypes.c_int64),('LimitFlags',wintypes.DWORD),('MinWorking',ctypes.c_size_t),('MaxWorking',ctypes.c_size_t),('ActiveProcesses',wintypes.DWORD),('Affinity',ctypes.c_size_t),('Priority',wintypes.DWORD),('Scheduling',wintypes.DWORD)]
            class Counters(ctypes.Structure):
                _fields_=[(name,ctypes.c_uint64) for name in ['ReadOp','WriteOp','OtherOp','ReadBytes','WriteBytes','OtherBytes']]
            class Extended(ctypes.Structure):
                _fields_=[('Basic',Basic),('IO',Counters),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcessMemory',ctypes.c_size_t),('PeakJobMemory',ctypes.c_size_t)]
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateJobObjectW.restype=wintypes.HANDLE
            kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
            kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            job=kernel.CreateJobObjectW(None,None)
            limits=Extended();limits.Basic.LimitFlags=0x2000|0x100|0x8
            limits.Basic.ActiveProcesses=1;limits.ProcessMemory=memory_mb*1024*1024
            if not job or not kernel.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job,wintypes.HANDLE(int(process._handle))):
                raise RuntimeError('Cannot establish extraction process limits')
        stdout,stderr=process.communicate(input=input_text,timeout=timeout)
        if len(stdout)>3000000 or len(stderr)>100000:
            raise RuntimeError('Extraction process output limit exceeded')
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
    finally:
        if process.poll() is None:
            process.kill();process.communicate()
        if job: kernel.CloseHandle(job)
