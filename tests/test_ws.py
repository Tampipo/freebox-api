
import asyncio
from freebox_api import Freepybox

async def demo():
    # Instantiate Freepybox class using default application descriptor
    # and default token_file location
    fbx = Freepybox(api_version="latest")
    await fbx.open("mafreebox.freebox.fr", "443")
    await fbx.ws.upload_file("test.txt", "/PauguySSD/Enregistrements", chunk_size=8192, overwrite=True, request_id=42)
    await fbx.close()

if __name__ == "__main__":
    asyncio.run(demo())