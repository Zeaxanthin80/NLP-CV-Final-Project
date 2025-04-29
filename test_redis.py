import redis
import sys

# Connect to Redis
r = redis.Redis.from_url('redis://localhost:6379/0')

# Get the most recent task ID
task_ids = r.keys('celery-task-meta-*')
if not task_ids:
    print("No task IDs found in Redis")
    sys.exit(1)

latest_task_id = task_ids[-1].decode('utf-8')
print(f"Latest task ID: {latest_task_id}")

# Get the task data
task_data = r.hgetall(latest_task_id)
print("\nTask data:")
for key, value in task_data.items():
    print(f"  {key.decode('utf-8')}: {value.decode('utf-8')}")

# Add a test transcript to Redis
test_transcript = "This is a test transcript. It should appear in the UI."
print(f"\nAdding test transcript to {latest_task_id}")
r.hset(latest_task_id, 'result', test_transcript)
r.hset(latest_task_id, 'status', 'success')

print("\nUpdated task data:")
task_data = r.hgetall(latest_task_id)
for key, value in task_data.items():
    print(f"  {key.decode('utf-8')}: {value.decode('utf-8')}")

print("\nNow refresh your browser and check if the transcript appears.")
