# Task: Scaling Strategies (Worker Queues & Dynamic Batching)

## Context
To handle higher loads, we need better scaling mechanisms.

## Objective
1. **Worker Queues**: Implement a task queue (e.g., Redis/Celery) to decouple API requests from GPU execution.
2. **Dynamic Batching**: Implement middleware that collects incoming requests over a short window and batches them together.
3. **Multi-GPU Orchestration**: Plan for distributing models or requests across multiple GPUs.
