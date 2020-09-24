# Web server

Простой http сервер

## Архитектура 

ThreadPool

## Результаты нагрузочных тестов

### Окружение

```
macbook pro, 4 CPU, 16 Gb RAM
```

### Запуск сервера

```shell script
python httpd.py -w 1000
```

### Запуск теста 1

```shell script
ab -n 10000 -c 100 -r http://localhost:8080/
```

### Результаты 1

```shell script
Server Software:        WebServer/1.0
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   4.687 seconds
Complete requests:      10000
Failed requests:        0
Non-2xx responses:      10000
Total transferred:      1290000 bytes
HTML transferred:       0 bytes
Requests per second:    2133.66 [#/sec] (mean)
Time per request:       46.868 [ms] (mean)
Time per request:       0.469 [ms] (mean, across all concurrent requests)
Transfer rate:          268.79 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.4      0       5
Processing:     6   46   5.2     45      91
Waiting:        1   46   5.1     45      89
Total:          6   47   5.1     46      91

Percentage of the requests served within a certain time (ms)
  50%     46
  66%     47
  75%     49
  80%     50
  90%     52
  95%     55
  98%     60
  99%     63
 100%     91 (longest request)
```

### Запуск теста 2

```shell script
ab -n 10000 -c 100 -r http://localhost:8080/README.md
```

### Результаты 2

```
Server Software:        WebServer/1.0
Server Hostname:        localhost
Server Port:            8080

Document Path:          /README.md
Document Length:        1953 bytes

Concurrency Level:      100
Time taken for tests:   16.360 seconds
Complete requests:      10000
Failed requests:        0
Total transferred:      20930000 bytes
HTML transferred:       19530000 bytes
Requests per second:    611.23 [#/sec] (mean)
Time per request:       163.605 [ms] (mean)
Time per request:       1.636 [ms] (mean, across all concurrent requests)
Transfer rate:          1249.32 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.4      0       8
Processing:    10  163  27.0    157     482
Waiting:       10  162  26.8    156     477
Total:         15  163  26.9    157     485

Percentage of the requests served within a certain time (ms)
  50%    157
  66%    162
  75%    165
  80%    168
  90%    179
  95%    227
  98%    245
  99%    269
 100%    485 (longest request)

```