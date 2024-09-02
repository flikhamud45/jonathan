import argparse
import time
import asyncio
import aiohttp
import matplotlib.pyplot as plt
import math

results = {}
results_lock = asyncio.Lock()
errors = {}
errors_lock = asyncio.Lock()

async def send_request(url):
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                end_time = time.time()
                if response.status != 200:
                    async with errors_lock:
                        errors[end_time] = response.status
    except aiohttp.ClientError as e:
        end_time = time.time()
        async with errors_lock:
            errors[end_time] = str(e)

    async with results_lock:
        results[end_time] = end_time - start_time

async def run_workload(qps, duration, url):
    time_interval = 1 / qps
    tasks = []
    start_time = time.time()
    prev_time = start_time
    for i in range(duration):
        for j in range(qps):
            task = asyncio.ensure_future(send_request(url))
            tasks.append(task)
            curr_time = time.time()
            if curr_time - prev_time < time_interval:
                await asyncio.sleep(time_interval - (curr_time - prev_time))
            else:
                print("Warning: the workload is too high for the current machine")
            prev_time = time.time()
    
    # wait for all requests to finish
    await asyncio.gather(*tasks)

async def run_big_workload(args):
    # prev_time = time.time()
    tasks = []
    for i in range(args.qps // args.dividor):
        task = asyncio.ensure_future(run_workload(args.dividor, args.duration, args.url))
        tasks.append(task)
        # curr_time = time.time()
        # if curr_time - prev_time < math.ceil(args.devidor/args.qps):
        #     time.sleep(math.ceil(args.devidor/args.qps) - (curr_time - prev_time))
    if args.qps % args.dividor != 0:
        task = asyncio.ensure_future(run_workload(args.qps % args.dividor, args.duration, args.url))
        tasks.append(task)
    
    # wait for all requests to finish
    await asyncio.gather(*tasks)


def convert_to_seconds(time_str):
    if time_str[-1] == 's':
        return int(time_str[:-1])
    elif time_str[-1] == 'm':
        return int(time_str[:-1]) * 60
    elif time_str[-1] == 'h':
        return int(time_str[:-1]) * 3600
    else:
        return int(time_str)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Create a workload.')
    parser.add_argument('--qps', type=int, default=100, help='Queries per second.') 
    parser.add_argument('--duration', type=str, default='5m', help='Duration of the workload.')
    parser.add_argument('--url', type=str, default='http://34.123.107.154/productpage', help='URL to send the queries.')
    parser.add_argument('--dividor', type=int, default=0, help='Dividor for the qps.')

    args = parser.parse_args()

    print(f"Creating a workload with {args.qps} queries per second for {args.duration}.")
    args.duration = convert_to_seconds(args.duration)
    if not args.url.startswith('http'):
        args.url = 'http://' + args.url

    # Run the workload
    if args.dividor:
        asyncio.run(run_big_workload(args))
    else:
        asyncio.run(run_workload(args.qps, args.duration, args.url))

    
    
    print("Workload completed.")

    # Plot the results
    plt.plot(results.keys(), results.values())
    plt.xlabel('Query number')
    plt.ylabel('Response time (s)')
    plt.title('Response time of queries')
    plt.show()

    # plot the errors
    plt.plot(errors.keys(), errors.values())
    plt.xlabel('Time (s)')
    plt.ylabel('Error')
    plt.title('Errors')
    plt.show()


if __name__ == '__main__':
    main()
