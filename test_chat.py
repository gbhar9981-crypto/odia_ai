import httpx
import json
import asyncio

async def test_chat_stream():
    url = "http://10.62.124.77:8000/api/chat/stream"
    payload = {
        "message": "ନମସ୍କାର, କେମିତି ଅଛ?",
        "thread_id": 1
    }
    
    print(f"Testing Chat Stream at {url}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    return
                    
                print("Response received: ", end="", flush=True)
                async for chunk in response.aiter_text():
                    print(chunk, end="", flush=True)
                print("\n\nTest Passed!")
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat_stream())
