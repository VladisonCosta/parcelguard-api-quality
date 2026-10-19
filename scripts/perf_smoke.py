"""Informal LOCAL latency sample, not a load test or performance SLA."""
import argparse
import statistics
import time
import httpx


def main():
    parser=argparse.ArgumentParser(description='Local latency smoke sample; not a load test')
    parser.add_argument('--url',default='http://127.0.0.1:8001/health')
    parser.add_argument('--requests',type=int,default=100)
    args=parser.parse_args()
    if args.requests < 1 or args.requests > 1000:
        parser.error('--requests must be between 1 and 1000')
    timings=[]
    with httpx.Client(timeout=5) as client:
        for _ in range(args.requests):
            start=time.perf_counter()
            resp=client.get(args.url)
            resp.raise_for_status()
            timings.append((time.perf_counter()-start)*1000)
    values=sorted(timings)
    p95=values[max(0,int(len(values)*.95)-1)]
    print(f'URL: {args.url}')
    print(f'Requests: {len(values)} | p50: {statistics.median(values):.2f}ms | p95: {p95:.2f}ms | max: {max(values):.2f}ms')
    print('Informal single-client local smoke only. No performance SLA is implied.')

if __name__=='__main__': main()
