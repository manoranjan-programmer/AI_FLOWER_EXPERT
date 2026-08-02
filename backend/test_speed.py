import asyncio
import time
import chatbot

async def main():
    chatbot.load()
    print("Model loaded. Sending streaming chat request...")
    t0 = time.perf_counter()
    count = 0
    async for token in chatbot.generate_stream_async("Give 2 medicinal uses of Rose"):
        count += 1
        if count == 1:
            print(f"Time to FIRST token: {time.perf_counter() - t0:.3f} s")
    print(f"Total stream time for {count} tokens: {time.perf_counter() - t0:.3f} s")

if __name__ == "__main__":
    asyncio.run(main())
