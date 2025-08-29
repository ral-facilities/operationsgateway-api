# Concurrency

Broadly speaking, concurrency is ["the ability to run \[multiple tasks\] in an overlapping manner"](https://realpython.com/async-io-python/). It is related, but subtly different to other terms like parallelism, multiprocessing etc. Strict definitions aside, our primary motivation is the same: to decrease the time taken by the application to return a response.

## Inter-request concurrency

In accordance with the recommendations in the [FastAPI documentation](https://fastapi.tiangolo.com/async/), OperationsGateway API defines its endpoints as `async`. This makes the application more efficient when serving multiple requests. By looking at the command used to run the application in production:

```bash
gunicorn operationsgateway_api.src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker -t 300 --max-requests 500
```

There are a number of relevant arguments. [`UvicornWorker`](https://github.com/Kludex/uvicorn-worker) is a class which supports the use of Python's [`asyncio`](https://docs.python.org/3/library/asyncio.html) event loop. Each worker can accept a request, and will execute this request in the event loop. Synchronous code will be executed until an `await` is reached. The outer function is "paused" until the co-routine which is awaited returns. This co-routine might contain its own `await`s, which will also be "paused" while the next nested co-routine is awaited by the loop. Eventually, we end up awaiting something that is I/O bound. In our application, this could be calls to MongoDB or Echo. At this point, there is no more synchronous code the worker can execute, so our compute resources are effectively not being used until it completes.

By specifying that a worker can process up to `500` max requests, it means that other requests from the same or another user can be processed by the worker by adding it to the worker's event loop. These will execute in the same way, but it's now possible that a co-routine from either request might `return`. Whichever does is then processed by the event loop until the next `await`.

Finally, we specify `4` workers (each corresponding to their own process), making use of the available CPU cores. This adds another layer of simple parallelism - each worker process can be executing up to `500` requests independently. This is why some lifespan tasks should be restricted to a single worker.

Overall, this means we can process up to 2000 requests from users at the same time by allowing the worker processes to do the CPU bound synchronous work for a single request at the same time as I/O bound work for any number of other requests is awaited.

## Intra-request concurrency

While the above can offer a significant benefit when the application has multiple users, and can be implemented by following the standard FastAPI documentation, it does not speed up a single, long running request as that request will execute each co-routine in series.

The longest running request for the application are exports requiring 100s or 1000s of objects to be downloaded from Echo. Originally, this was done sequentially and synchronously whilst being significantly I/O bound (waiting for Echo to return the requested bytes typically taking around 0.7 seconds).

To achieve a speed-up for single requests, it must be possible for a single request to result in multiple I/O bound co-routines being awaited by the event loop at the same time.

### Implementation

- Replace [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) with [aioboto3](https://github.com/terricain/aioboto3), which allows us to await downloads from object storage.
- Use [TaskGroup](https://docs.python.org/3/library/asyncio-task.html#task-groups) (note that there are other ways of achieving this type of concurrency, but TaskGroup seemed like a fairly high level and intuitive way of doing this) to create and await multiple co-routines:
  - When exporting multiple records
    - When exporting multiple channels per records
  - When evaluating functions for multiple records
    - When getting the data (that the function(s) depend on) for multiple channels per record
- Additionally, there is an overhead when creating the connection to Echo using the `boto3` and `aioboto3` clients (around 0.4 seconds). This can be avoided by using the FastAPI lifespan to hold `async` context managers open and `lru_cache` to return a cached instance of the interface so that we do not spend time repeating initialization of the connections.

Note that these changes are highly interdependent on each other in order to have a benefit. If only `aioboto3` was implemented then things would actually take longer (as it has a higher overhead when initialising). `TaskGroups` cannot be used without an `async` call to object storage to `await`. And the method of caching the initialised interface needs to be different for `aioboto3` compared to `boto3` since the former uses context managers.

As a consequence of making this change, there are multiple functions which are now `async` and need to be awaited, and some existing logic needed to be refactored so that it was possible to replace serial code execution with a `for` loop that builds the `TaskGroup`.
