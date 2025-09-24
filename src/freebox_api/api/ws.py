"""
File System API.
https://dev.freebox.fr/sdk/os/fs/
"""
import asyncio
import base64
import logging
import os
import ssl
from typing import Dict
import websockets
import freebox_api.exceptions
from freebox_api.access import Access
import json

logger = logging.getLogger(__name__)



class Ws:
    """
    WebSocket
    """

    def __init__(self, access: Access, api_version: str = "latest"):
        self._access = access
        self.api_version = api_version
        self.endpoint = f"wss://mafreebox.freebox.fr/api/{self.api_version}/ws/upload"

    async def upload_file(self, file_path: str, dirname: str, chunk_size: int = 4096, overwrite: bool = True, request_id: int = 1):
        """
        Upload a file to the Freebox using WebSocket.
        """
        ssl_context = ssl._create_unverified_context()  # ignore SSL verification

        session_token = await self._access.get_session_token()

        headers = {
            "X-Fbx-App-Auth": session_token
        }

        async with websockets.connect(self.endpoint, ssl=ssl_context, extra_headers=headers) as websocket:
            start = await self._start_upload(websocket, file_path, dirname, overwrite, request_id)
            if not start:
                raise freebox_api.exceptions.HttpRequestError("Failed to start upload")

            # Upload file in chunks
            await self._upload_file_chunks(websocket, file_path, chunk_size=chunk_size)

            # Finalize upload
            stop = await self._finalize_upload(websocket, request_id)
            if not stop:
                raise freebox_api.exceptions.HttpRequestError("Failed to finalize upload")
        return True
    
    async def _start_upload(self, websocket, file_path: str, dirname: str, overwrite: bool, request_id: int):
        """
        Start the file upload process.
        """
        # Read file size
        file_size = os.path.getsize(file_path)
        dirname_b64 = base64.b64encode(dirname.encode()).decode()
        filename = os.path.basename(file_path)

        # Start upload
        start_msg = {
            "action": "upload_start",
            "request_id": request_id,
            "size": file_size,
            "dirname": dirname_b64,
            "filename": filename,
        }
        if overwrite:
            start_msg["force"] = "overwrite"
        await websocket.send(json.dumps(start_msg))
        response = await websocket.recv()
        resp_json = json.loads(response)
        if not resp_json.get("success"):
            print("Upload start failed:", resp_json.get("msg"))
            return
        return True
    
    async def _finalize_upload(self, websocket, request_id: int):
        """
        Finalize the upload process.
        """
        finalize_msg = {
            "action": "upload_finalize",
            "request_id": request_id
        }
        await websocket.send(json.dumps(finalize_msg))
        response = await websocket.recv()
        resp_json = json.loads(response)
        if not resp_json.get("success"):
            print("Upload finalize failed:", resp_json.get("msg"))
            return
        return True
        
    async def _upload_file_chunks(self, websocket, file_path: str, chunk_size: int):
        """
        Upload file in chunks.
        """
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                await websocket.send(chunk)
                await asyncio.sleep(0.01)  # slight delay to avoid overwhelming the server
            
            response = await websocket.recv()
            resp_json = json.loads(response)
            if not resp_json.get("success"):
                print("Chunk upload failed:", resp_json.get("msg"))
                return
        return True