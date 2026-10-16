# Task: Concurrency and Async I/O Optimization

## Context
Blocking tasks like file saving or network operations can hinder throughput.

## Objective
1. **Async I/O**: Ensure all file saving and network-bound tasks (like downloading weights) are fully asynchronous to prevent blocking the main execution thread.

## Relevant Files
- `src/generators/image/image_generator.py`
- `src/generators/image/text_expander.py`
