#!/usr/bin/env python3

from nano.server.socketwrapper         import SocketWrapper

import threading
import sys

"""
    Class for manage http file download
"""
class FileBuffer(threading.Thread):


    """
        Constructor
        @param   conn               socket.socket   Socket demandant un fichier
        @param   path               str             Chemin d'accès au fichier
        @param   byteStart          int             Index de l'octet de depart a téléchager
        @param   byteLength         int             Nombre d'octets a télécharger
        @param   bandWidthChunkSize int             Taille des tronçons a envoyer
        @param   bandWidthDelay     int             Delai entre 2 envoi de tronçon
        @returns None
    """
    def __init__(self, conn: SocketWrapper, path: str, byteStart: int, byteLength: int, bandWidthChunkSize: int, bandWidthDelay: int):
        threading.Thread.__init__(self)
        self._conn       = conn
        self._path       = path
        self._byteStart  = byteStart
        self._byteLength = byteLength
        self._chunkSize  = bandWidthChunkSize
        self._delay      = bandWidthDelay

    """
        Destructeur
        @returns None
    """
    def __del__(self):
        self._conn.close()

    """
        Routine de threading.Thread gerant le téléchargement
        @returns None
    """
    def run(self):
        eof         = False
        fd          = open(self._path, "rb")

        # Position to byteStart
        if self._byteStart>0:
            fd.seek(self._byteStart)
        start       = 0
        length      = self._byteLength
        chunksize   = 0

        # Read loop
        while not self._conn.closed and not eof:
            chunksize = self._chunkSize
            if start+chunksize>length:
                chunksize = length-start
                eof = True
            chunk = fd.read(chunksize) #bytes(fd.read(chunksize), encoding='ascii')
            self._conn.write(chunk)
            start += chunksize

            if not eof:
                time.sleep(self._delay/1000)
        
        if not self._conn.closed:
            self._conn.close()

        sys.exit(0)
