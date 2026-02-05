from lib.task_storage import TaskStorage
from lib.task_model import TaskStatus

def test_save_task_preserves_user_edits(tmp_path):
    """Test that save_task with update_body=False preserves manual edits to the file."""
    # Setup storage in temp dir
    storage = TaskStorage(data_root=tmp_path)
    
    # 1. Create a task
    task = storage.create_task(
        title="Test Task",
        body="Original body"
    )
    storage.save_task(task)
    task_id = task.id
    
    # 2. Simulate agent holding a reference to the task (t1)
    t1 = storage.get_task(task_id)
    assert "Original body" in t1.body
    
    # 3. Simulate user manually editing the file on disk
    task_path = storage._find_task_path(task_id)
    original_content = task_path.read_text(encoding="utf-8")
    new_content = original_content + "\n\nUser manual note"
    task_path.write_text(new_content, encoding="utf-8")
    
    # Verify user edit is there
    t_check = storage.get_task(task_id)
    assert "User manual note" in t_check.body
    
    # 4. Agent updates t1 (which has stale body) and saves with preservation
    t1.status = TaskStatus.DONE
    storage.save_task(t1, update_body=False)
    
    # 5. Verify file has NEW status but PRESERVED body
    t_final = storage.get_task(task_id)
    assert t_final.status == TaskStatus.DONE
    assert "Original body" in t_final.body
    assert "User manual note" in t_final.body

def test_save_task_overwrites_when_requested(tmp_path):
    """Test that save_task with update_body=True (default) overwrites manual edits."""
    storage = TaskStorage(data_root=tmp_path)
    
    # 1. Create a task
    task = storage.create_task(
        title="Overwrite Task",
        body="Original body"
    )
    storage.save_task(task)
    task_id = task.id
    
    # 2. Agent holds reference
    t1 = storage.get_task(task_id)
    
    # 3. User edits file
    task_path = storage._find_task_path(task_id)
    original_content = task_path.read_text(encoding="utf-8")
    task_path.write_text(original_content + "\n\nUser note", encoding="utf-8")
    
    # 4. Agent updates t1 and saves (default update_body=True)
    t1.status = TaskStatus.DONE
    storage.save_task(t1)  # Default is True
    
    # 5. Verify file has NEW status and OLD body (user note lost)
    t_final = storage.get_task(task_id)
    assert t_final.status == TaskStatus.DONE
    assert "Original body" in t_final.body
    assert "User note" not in t_final.body
