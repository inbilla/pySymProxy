from __future__ import print_function
# Import print() function for Python 2.7 compatibility

import ctypes
import ctypes.wintypes
import os
import sys
import uuid
import threading
from shutil import copyfile
import logging

logger = logging.getLogger(__name__)

class dbghelp:
    g_shareDll = True;
    g_uniqueInitializationHandle = 1
    g_lock = threading.RLock()

    def __init__(self, localCachePath, serverCachePath, server):
        self._localCachePath = localCachePath
        self._serverCachePath = serverCachePath
        self._server = server

        if dbghelp.g_shareDll:
            self._lock = threading.RLock()
        else:
            self._lock = dbghelp.g_lock

        self._uniqueProcessHandle = dbghelp.g_uniqueInitializationHandle
        dbghelp.g_uniqueInitializationHandle = dbghelp.g_uniqueInitializationHandle + 1

        self.initialize()

    def __del__(self):
        self.SymCleanup(self._uniqueProcessHandle)

    def symCallbackProc(self, process, actionCode, callbackData, context):
        with self._lock:
            if actionCode == self.CBA_EVENT or \
                            actionCode == self.CBA_SRCSRV_EVENT:

                class CBA_EVENT_DATA(ctypes.Structure):
                    _fields_ = [
                        ('severity', ctypes.c_ulong),
                        ('code', ctypes.c_ulong),
                        ('desc', ctypes.c_char_p),
                        ('object', ctypes.c_void_p)]

                data = ctypes.cast(callbackData, ctypes.POINTER(CBA_EVENT_DATA))
                message = data[0].desc.replace("\b", "").strip()
                logger.info("dllEvent {}>({}) {}".format(self._uniqueProcessHandle, data[0].code, message))
                return 1
            elif actionCode == 0x07:
                # Opportunity to cancel a download.
                # always returning false here
                wantToCancel = 0
                return wantToCancel
            elif actionCode == 0x08:
                # Event that indicates that setOptions has been called and applied new options to the system.
                # Don't need to know about this in our code
                return 1
            else:
                logger.info("dllEvent {}> unknown event {}".format(self._uniqueProcessHandle, actionCode))

        return 0

    def initialize(self):
        self.loadDll()

        # Calculate the symbol path
        self._sympath = "srv*"
        if (self._localCachePath != None):
            self._sympath += self._localCachePath + "*"
        if (self._serverCachePath != None):
            self._sympath += self._serverCachePath + "*"
        self._sympath += self._server

        SYMOPT_DEBUG = 0x80000000
        symoptions = self.SymGetOptions()
        symoptions |= SYMOPT_DEBUG
        self.SymSetOptions(symoptions)

        # Initialize the symbol system
        success = self.SymInitialize(self._uniqueProcessHandle, ctypes.c_char_p(self._sympath), ctypes.c_bool(False))
        if (success == False):
            raise ctypes.WinError()

        # Setup debug callback to hook logging
        success = self.SymRegisterCallback(self._uniqueProcessHandle, self.callback, 0)
        if (success == False):
            raise ctypes.WinError()


    def loadDll(self):
        try:
            dllName = "./dbghelp/dbghelp.dll"

            if not (os.path.exists(dllName)):
                logger.error("dbghelp.dll and symsrv.dll must be placed in the dbghelp folder.")
                logger.error("These files can be downloaded in the Debugging Tools for Windows SDK.")
                raise Exception("dbghelp.dll and symsrv.dll are not in the expected location")

            if dbghelp.g_shareDll:
                targetName = dllName + "." + str(self._uniqueProcessHandle) + ".dll"
                copyfile(dllName, targetName)
                dllName = targetName

            self.dbghelp_dll = ctypes.windll.LoadLibrary(dllName)
            logger.info("Loaded dll: {}".format(dllName))

        except WindowsError as e:
            print(e)
            raise

        self.SymInitialize = self.dbghelp_dll["SymInitialize"]
        self.SymInitialize.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_bool]
        self.SymInitialize.restype = ctypes.c_ulong
        self.SymSetOptions = self.dbghelp_dll["SymSetOptions"]
        self.SymSetOptions.argtypes = [ctypes.c_ulong]
        self.SymSetOptions.restype = ctypes.c_ulong
        self.SymGetOptions = self.dbghelp_dll["SymGetOptions"]
        self.SymGetOptions.argtypes = []
        self.SymGetOptions.restype = ctypes.c_ulong
        self.SymCleanup = self.dbghelp_dll["SymCleanup"]
        self.SymCleanup.argtypes = [ctypes.c_ulong]
        self.SymCleanup.restype = ctypes.c_ulong
        self.SymFindFileInPath = self.dbghelp_dll["SymFindFileInPath"]
        self.SymFindFileInPath.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
            ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p]
        self.SymFindFileInPath.restype = ctypes.c_ulong
        self.SymFindFileInPath_pdb = self.dbghelp_dll["SymFindFileInPath"]
        self.SymFindFileInPath_pdb.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                                           ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_char_p,
                                           ctypes.c_void_p, ctypes.c_void_p]
        self.SymFindFileInPath_pdb.restype = ctypes.c_ulong

        self.SymRegisterCallbackProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p)
        self.SymRegisterCallback = self.dbghelp_dll["SymRegisterCallback"]
        self.SymRegisterCallback.argtypes = [ctypes.c_ulong, self.SymRegisterCallbackProc, ctypes.c_void_p]
        self.SymRegisterCallback.restype = ctypes.c_ulong
        self.callback = self.SymRegisterCallbackProc(self.symCallbackProc)

        self.SSRVOPT_DWORD = 0x00000002
        self.SSRVOPT_DWORDPTR = 0x00000004
        self.SSRVOPT_GUIDPTR = 0x00000008

        self.CBA_EVENT = 0x00000010
        self.CBA_SRCSRV_EVENT = 0x40000000

    def extractIdentifiers_Pdb(self, id):
        return (
            #bytearray.fromhex(id[:32])
            uuid.UUID(id[:32]),
            int(id[32:], 16))

    def extractIdentifiers_Binary(self, id):
        return (
            int(id[:8], 16),
            int(id[8:], 16))

    def findFile(self, name, identifier):
        logger.info("Find request: {}/{}".format(name, identifier))
        result = None
        try:
            with self._lock:
                if name.lower().endswith(".pdb"):
                    result = self.findFile_Pdb(name, identifier)
                else:
                    result = self.findFile_Binary(name, identifier)
        except Exception:
            raise
        finally:
            logger.info("Find result: {}".format(result))
        return result

    def findFile_Binary(self, name, identifier):
        (id1, id2) = self.extractIdentifiers_Binary(identifier)

        fileLocation = ctypes.create_string_buffer(b'\000' * 1024)
        flags = self.SSRVOPT_DWORD
        result = self.SymFindFileInPath(self._uniqueProcessHandle, self._sympath, name, id1, id2, 0, flags, fileLocation, None, None)
        if (not result):
            raise ctypes.WinError()

        return fileLocation.value

    def findFile_Pdb(self, name, identifier):
        (id1, id2) = self.extractIdentifiers_Pdb(identifier)

        #convert guid to a pointer to a guid buffer
        id1 = bytearray(id1.bytes_le)
        id1 = (ctypes.c_ubyte * len(id1)).from_buffer(id1)

        fileLocation = ctypes.create_string_buffer(b'\000' * 1024)
        flags = self.SSRVOPT_GUIDPTR
        result = self.SymFindFileInPath_pdb(self._uniqueProcessHandle, self._sympath, name, ctypes.byref(id1), id2, 0,
                                        flags, fileLocation, None, None)

        # if the search reports unsuccessful, it is possible it still
        # succeeded. This appears common with long distance servers with high latency.
        # Check if the file exists in the location we might expect:
        if not result:
            possible_location = "{}/{}/{}/{}".format(self._localCachePath, name, identifier, name)
            if os.path.isfile(possible_location):
                logger.info("DbgHlp reported unable to find, but file was found locally anyway, returning local file. {}".format(possible_location))
                fileLocation.value = possible_location
                result = True

        if (not result):
            raise ctypes.WinError()

        return fileLocation.value