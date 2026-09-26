"""Thin ctypes binding: inference uses only the bundled native component."""
import ctypes as C
import json
import math
from pathlib import Path
import platform
import threading
import atexit


_default_lock = threading.RLock()
_default_session = None


def _bundled_directory():
    """Find installed assets, or this checkout's platform release, never the cwd."""
    package = Path(__file__).resolve().parent
    bundled = package / '_bundle'
    if bundled.is_dir():
        return bundled
    system, machine = platform.system(), platform.machine().lower()
    target = {('Darwin', 'arm64'): 'macos-arm64',
              ('Windows', 'amd64'): 'windows-x64',
              ('Windows', 'x86_64'): 'windows-x64',
              ('Linux', 'x86_64'): 'linux-x64'}.get((system, machine))
    checkout = package.parent / 'released' / (target or 'unsupported')
    if target and checkout.is_dir():
        return checkout
    raise DecisionGatorError(2, 'No bundled DecisionGator component for this platform. '
                             'Install platform assets in decisiongator/_bundle, '
                             'or use Session.load(path) for a custom bundle.')


def is_yes_p(content, question, criteria=None):
    """Return the estimated probability of yes using the bundled component.

    The first call initializes a shared session; later calls reuse it. Calls are
    serialized and initialization failures can be retried. No downloads occur.
    Use Session.load for custom bundles or explicitly managed sessions.
    """
    global _default_session
    with _default_lock:
        if _default_session is None:
            _default_session = Session.load(_bundled_directory())
        return _default_session.evaluate(content, question, criteria)


def is_yes(content, question, criteria=None, *, threshold=0.5):
    """Return whether the probability of yes is >= threshold (default 0.5).

    The threshold must be a finite number between zero and one inclusive.
    Invalid thresholds raise ValueError; evaluation errors propagate, never False.
    """
    _threshold(threshold)
    return is_yes_p(content, question, criteria) >= threshold


def _threshold(threshold, name='threshold'):
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError(f'{name} must be a finite number between 0 and 1')
    if not 0 <= threshold <= 1 or not math.isfinite(threshold):
        raise ValueError(f'{name} must be a finite number between 0 and 1')
    return threshold


def choose_p(content, question, options, criteria=None):
    """Rank options for a question about the content.

    Returns a list of (index, probability) pairs, best first, one per option;
    probabilities sum to one and index refers to the caller's options list.
    Equal probabilities keep the caller's order. Uses the shared bundled session.
    """
    global _default_session
    with _default_lock:
        if _default_session is None:
            _default_session = Session.load(_bundled_directory())
        return _default_session.evaluate_choice(content, question, options, criteria)


def choose(content, question, options, criteria=None, *, threshold=0.0):
    """Return the index of the best option, or None if its probability is below threshold.

    The default threshold of 0 never returns None. Errors propagate, never None.
    """
    _threshold(threshold)
    index, probability = choose_p(content, question, options, criteria)[0]
    return index if probability >= threshold else None


def _close_default():
    global _default_session
    with _default_lock:
        if _default_session is not None:
            _default_session.close()
            _default_session = None


atexit.register(_close_default)


class DecisionGatorError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class _Criteria(C.Structure):
    _fields_ = [('yes', C.c_char_p), ('yes_bytes', C.c_size_t), ('no', C.c_char_p), ('no_bytes', C.c_size_t)]


class Session:
    @classmethod
    def load(cls, path):
        return cls(path)

    def __init__(self, path):
        self._lock = threading.RLock()
        self._handle = C.c_void_p()
        directory = Path(path).resolve()
        name = {'Darwin':'libdecisiongator.dylib','Linux':'libdecisiongator.so','Windows':'decisiongator.dll'}[platform.system()]
        self._lib = C.CDLL(str(directory/name))
        lib = self._lib
        lib.dg_load.argtypes = [C.c_char_p, C.c_size_t, C.POINTER(C.c_void_p)]
        lib.dg_load.restype = C.c_int32
        lib.dg_evaluate.argtypes = [C.c_void_p,C.c_char_p,C.c_size_t,C.c_char_p,C.c_size_t,C.POINTER(_Criteria),C.POINTER(C.c_double)]
        lib.dg_evaluate.restype = C.c_int32
        lib.dg_evaluate_choice.argtypes = [C.c_void_p,C.c_char_p,C.c_size_t,C.c_char_p,C.c_size_t,C.POINTER(C.c_char_p),C.POINTER(C.c_size_t),C.c_size_t,C.POINTER(_Criteria),C.POINTER(C.c_int32),C.POINTER(C.c_double)]
        lib.dg_evaluate_choice.restype = C.c_int32
        lib.dg_release.argtypes = [C.c_void_p]; lib.dg_release.restype = None
        lib.dg_last_error.argtypes = [C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        lib.dg_last_error.restype = C.c_int32
        lib.dg_metadata.argtypes = [C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        lib.dg_metadata.restype = C.c_int32
        encoded = str(directory).encode('utf-8')
        self._check(lib.dg_load(encoded,len(encoded),C.byref(self._handle)))

    def _check(self, status):
        if status:
            required = C.c_size_t()
            self._lib.dg_last_error(None,0,C.byref(required))
            buf = C.create_string_buffer(max(1,required.value))
            self._lib.dg_last_error(buf,len(buf),C.byref(required))
            raise DecisionGatorError(status,buf.value.decode('utf-8',errors='replace'))

    def _open(self):
        if not self._handle: raise DecisionGatorError(1,'Session is closed')

    @staticmethod
    def _criteria(criteria):
        if criteria is None:
            return None
        if not isinstance(criteria,dict) or set(criteria) != {'yes','no'}:
            raise ValueError('criteria must contain yes and no')
        yes, no = criteria['yes'].encode('utf-8'), criteria['no'].encode('utf-8')
        return _Criteria(yes,len(yes),no,len(no))

    def evaluate(self, content, question, criteria=None):
        with self._lock:
            self._open()
            content, question = content.encode('utf-8'), question.encode('utf-8')
            native_criteria = self._criteria(criteria)
            result = C.c_double()
            self._check(self._lib.dg_evaluate(self._handle,content,len(content),question,len(question),C.byref(native_criteria) if native_criteria is not None else None,C.byref(result)))
            return result.value

    def evaluate_choice(self, content, question, options, criteria=None):
        """Return (index, probability) pairs for options, best first."""
        if isinstance(options, (str, bytes)) or not all(isinstance(o, str) for o in options):
            raise ValueError('options must be a list of strings')
        options = list(options)
        if len(options) < 2:
            raise ValueError('options must contain at least two entries')
        with self._lock:
            self._open()
            content, question = content.encode('utf-8'), question.encode('utf-8')
            native_criteria = self._criteria(criteria)
            encoded = [o.encode('utf-8') for o in options]
            pointers = (C.c_char_p * len(encoded))(*encoded)
            lengths = (C.c_size_t * len(encoded))(*[len(o) for o in encoded])
            indexes = (C.c_int32 * len(encoded))()
            probabilities = (C.c_double * len(encoded))()
            self._check(self._lib.dg_evaluate_choice(self._handle,content,len(content),question,len(question),pointers,lengths,len(encoded),C.byref(native_criteria) if native_criteria is not None else None,indexes,probabilities))
            return list(zip(indexes, probabilities))

    @property
    def metadata(self):
        with self._lock:
            self._open()
            required = C.c_size_t()
            self._check(self._lib.dg_metadata(self._handle,None,0,C.byref(required)))
            buffer = C.create_string_buffer(required.value)
            self._check(self._lib.dg_metadata(self._handle,buffer,len(buffer),C.byref(required)))
            return json.loads(buffer.value)

    def close(self):
        with self._lock:
            if self._handle:
                self._lib.dg_release(self._handle)
                self._handle = C.c_void_p()

    def __enter__(self):
        self._open()
        return self

    def __exit__(self,*args):
        self.close()
