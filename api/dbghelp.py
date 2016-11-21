import ctypes
import os
import sys
import uuid
import threading
from shutil import copyfile
import logging

g_uniqueInitializationHandle = 1
logger = logging.getLogger(__name__)

class dbghelp:
    def __init__(self, localCachePath, serverCachePath, server):
        self._localCachePath = localCachePath
        self._serverCachePath = serverCachePath
        self._server = server
        self._lock = threading.Lock()

        global g_uniqueInitializationHandle
        self._uniqueProcessHandle = g_uniqueInitializationHandle
        g_uniqueInitializationHandle = g_uniqueInitializationHandle + 1

        self.initialize()

    def __del__(self):
        self.SymCleanup(self._uniqueProcessHandle)

    def initialize(self):
        self.loadDll()

        # Calculate the symbol path
        self._sympath = "srv*"
        if (self._localCachePath != None):
            self._sympath += self._localCachePath + "*"
        if (self._serverCachePath != None):
            self._sympath += self._serverCachePath + "*"
        self._sympath += self._server

        # Initialize the symbol system
        success = self.SymInitialize(self._uniqueProcessHandle, ctypes.c_char_p(self._sympath), ctypes.c_bool(False))
        if (success == False):
            raise ctypes.WinError()

        SYMOPT_DEBUG = 0x80000000
        symoptions = self.SymGetOptions()
        symoptions |= SYMOPT_DEBUG
        self.SymSetOptions(symoptions)

    def loadDll(self):
        try:
            dllName = "./dbghelp/dbghelp.dll"

            if not (os.path.exists(dllName)):
                logger.error("dbghelp.dll and symsrv.dll must be placed in the dbghelp folder.")
                logger.error("These files can be downloaded in the Debugging Tools for Windows SDK.")
                raise Exception("dbghelp.dll and symsrv.dll are not in the expected location")

            targetName = dllName + "." + str(self._uniqueProcessHandle) + ".dll"

            copyfile(dllName, targetName)
            self.dbghelp_dll = ctypes.windll.LoadLibrary(targetName)
            logger.info("Loaded dll: {}".format(targetName))

        except WindowsError, e:
            print e
            raise

        self.SymInitialize = self.dbghelp_dll["SymInitialize"]
        self.SymInitialize.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_bool]
        self.SymInitialize.restype = ctypes.c_bool
        self.SymSetOptions = self.dbghelp_dll["SymSetOptions"]
        self.SymSetOptions.argtypes = [ctypes.c_ulong]
        self.SymSetOptions.restype = ctypes.c_ulong
        self.SymGetOptions = self.dbghelp_dll["SymGetOptions"]
        self.SymGetOptions.argtypes = []
        self.SymGetOptions.restype = ctypes.c_ulong
        self.SymCleanup = self.dbghelp_dll["SymCleanup"]
        self.SymCleanup.argtypes = [ctypes.c_ulong]
        self.SymCleanup.restype = ctypes.c_bool
        self.SymFindFileInPath = self.dbghelp_dll["SymFindFileInPath"]
        self.SymFindFileInPath.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
            ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p]
        self.SymFindFileInPath.restype = ctypes.c_bool
        self.SymFindFileInPath_pdb = self.dbghelp_dll["SymFindFileInPath"]
        self.SymFindFileInPath_pdb.argtypes = [ctypes.c_ulong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                                           ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_char_p,
                                           ctypes.c_void_p, ctypes.c_void_p]
        self.SymFindFileInPath_pdb.restype = ctypes.c_bool

        self.SSRVOPT_DWORD = 0x00000002
        self.SSRVOPT_DWORDPTR = 0x00000004
        self.SSRVOPT_GUIDPTR = 0x00000008

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

        if (not result):
            raise ctypes.WinError()

        return fileLocation.value