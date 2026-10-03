const response = await fetch(process.env.BENCH_BRIDGE_URL, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: process.argv[2],
});
console.log(await response.text());
if (!response.ok) process.exitCode = 1;
