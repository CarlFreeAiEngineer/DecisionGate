# Using the fast cores

Inference used a fixed four threads natively and one thread in browsers. It now uses one thread per fast physical core natively, and every logical core in a cross-origin isolated browser page. Predictions are unchanged: the Mac build matched the frozen platform comparison cases exactly, and the browser builds matched native results as before.

## How the thread count is chosen

ONNX Runtime splits each operation evenly across its threads, so the slowest core sets the pace. On chips that mix fast and slow cores, adding the slow ones makes calls slower. Hyperthreads share one core's arithmetic units and add nothing.

- **macOS and iOS:** the performance-cluster core count from the system (`hw.perflevel0.physicalcpu`), or the physical core count on Intel Macs.
- **Linux and Android:** Intel hybrid chips list their performance cores in `/sys/devices/cpu_core/cpus`; ARM chips rate each core's capacity, and the big and middle clusters are kept. Physical cores are then counted once, ignoring hyperthreads.
- **Windows:** cores with the highest efficiency class, from `GetLogicalProcessorInformationEx`.
- **Everywhere:** never more than the process is allowed to use. `DECISIONGATOR_THREADS` overrides the count when a model loads.
- **Browsers:** browsers do not report which cores are fast, so a cross-origin isolated page uses `navigator.hardwareConcurrency` threads. Other pages stay on one thread, because threaded WebAssembly needs `SharedArrayBuffer`.

## Measurements

The 0.4.0 model, float32 ONNX export, on an M1 Pro (8 performance and 2 efficiency cores), 256-token input, warm p50:

| Threads | p50 | p95 |
| ---: | ---: | ---: |
| 4, previous default | 535 ms | 556 ms |
| 6 | 401 ms | 424 ms |
| 8, new default | 320 ms | 356 ms |
| 10, every core | 670 ms | 711 ms |

The Mac native library with a shorter realistic input: 404 ms at four threads, 269 ms at the new default of eight.

Linux, Intel i7-10750H (6 cores, 12 hyperthreads), float16 bundle, 60 calls: 2,492 ms at four threads, 1,878 ms at six (the new default), 2,019 ms at twelve. Detection reported 6.

Windows detection was run in the 2-core Windows build guest and reported 2. No Windows timing was taken.

Browsers on the M1 Pro, the 87 comparison cases, p50 per call:

| Browser | Isolated, threaded | Not isolated, one thread |
| --- | ---: | ---: |
| Chromium | 188 ms | 572 ms |
| Firefox | 317 ms | 571 ms |
| WebKit (Playwright) | 119 ms | 566 ms |

Reports: `reports/browser-*-threaded.json` and `reports/browser-chromium.json`.

## Not yet released

The published 0.4.0 bundles, wheels, JARs, npm packages, and browser assets still use the old thread counts. They change when those are rebuilt on each platform and published.
