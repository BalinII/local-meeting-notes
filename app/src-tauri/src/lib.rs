#[tauri::command]
fn scaffold_status() -> &'static str {
    "Local Meeting Notes Tauri scaffold is ready."
}

#[tauri::command]
fn review_capture(capture_id: String) -> Result<serde_json::Value, String> {
    let output = run_backend(&[
        "review",
        "show",
        "--capture-id",
        capture_id.as_str(),
        "--format",
        "json",
    ])?;
    serde_json::from_str(&output).map_err(|error| format!("Invalid backend JSON: {error}"))
}

#[tauri::command]
fn list_recent_captures(limit: Option<i64>) -> Result<serde_json::Value, String> {
    let limit_arg = limit.unwrap_or(12).clamp(1, 100).to_string();
    let output = run_backend(&["review", "recent", "--limit", limit_arg.as_str()])?;
    serde_json::from_str(&output).map_err(|error| format!("Invalid backend JSON: {error}"))
}

#[tauri::command]
fn session_library(sort: Option<String>, filter: Option<String>) -> Result<serde_json::Value, String> {
    let sort_value = sort.unwrap_or_else(|| "newest".to_string());
    let filter_value = filter.unwrap_or_else(|| "all".to_string());
    run_backend_json(&[
        "session",
        "library",
        "--sort",
        sort_value.as_str(),
        "--filter",
        filter_value.as_str(),
    ])
}

#[tauri::command]
fn session_search(query: String, limit: Option<i64>, scope: Option<String>) -> Result<serde_json::Value, String> {
    let limit_arg = limit.unwrap_or(120).clamp(1, 500).to_string();
    let scope_value = scope.unwrap_or_else(|| "all".to_string());
    run_backend_json(&[
        "session",
        "search",
        "--query",
        query.as_str(),
        "--limit",
        limit_arg.as_str(),
        "--scope",
        scope_value.as_str(),
    ])
}

#[tauri::command]
fn export_capture(capture_id: String, format: String) -> Result<String, String> {
    let output = run_backend(&[
        "export",
        "run",
        "--capture-id",
        capture_id.as_str(),
        "--format",
        format.as_str(),
    ])?;
    Ok(output.trim().to_string())
}

#[tauri::command]
fn session_dashboard() -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "list"])
}

#[tauri::command]
fn create_session(title: Option<String>) -> Result<serde_json::Value, String> {
    let mut args = vec!["session", "create"];
    if let Some(value) = title.as_deref() {
        args.push("--title");
        args.push(value);
    }
    run_backend_json(&args)
}
#[tauri::command]
fn create_planned_session(title: String, planned_start_at: Option<String>, notes: Option<String>) -> Result<serde_json::Value, String> {
    let mut args = vec!["session", "planned-create", "--title", title.as_str()];
    if let Some(value) = planned_start_at.as_deref() {
        args.push("--planned-start-at");
        args.push(value);
    }
    if let Some(value) = notes.as_deref() {
        args.push("--notes");
        args.push(value);
    }
    run_backend_json(&args)
}
#[tauri::command]
fn list_planned_sessions(limit: Option<i64>) -> Result<serde_json::Value, String> {
    let limit_arg = limit.unwrap_or(20).clamp(1, 100).to_string();
    run_backend_json(&["session", "planned-list", "--limit", limit_arg.as_str()])
}
#[tauri::command]
fn list_upcoming_sessions(limit: Option<i64>) -> Result<serde_json::Value, String> {
    let limit_arg = limit.unwrap_or(20).clamp(1, 100).to_string();
    run_backend_json(&["session", "upcoming-list", "--limit", limit_arg.as_str()])
}
#[tauri::command]
fn create_session_from_upcoming(title: String, planned_start_at: Option<String>, external_meeting_id: Option<String>) -> Result<serde_json::Value, String> {
    let mut args = vec!["session", "upcoming-create", "--title", title.as_str()];
    if let Some(value) = planned_start_at.as_deref() {
        args.push("--planned-start-at");
        args.push(value);
    }
    if let Some(value) = external_meeting_id.as_deref() {
        args.push("--external-meeting-id");
        args.push(value);
    }
    run_backend_json(&args)
}

#[tauri::command]
fn get_session(capture_id: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "get", "--capture-id", capture_id.as_str()])
}

#[tauri::command]
fn rename_session(capture_id: String, title: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "rename", "--capture-id", capture_id.as_str(), "--title", title.as_str()])
}

#[tauri::command]
fn start_session(capture_id: String, include_loopback: bool, include_microphone: bool) -> Result<serde_json::Value, String> {
    let mut args = vec!["session", "record-start", "--capture-id", capture_id.as_str()];
    if !include_loopback {
        args.push("--no-loopback");
    }
    if !include_microphone {
        args.push("--no-microphone");
    }
    run_backend_json(&args)
}

#[tauri::command]
fn pause_session(capture_id: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "pause", "--capture-id", capture_id.as_str()])
}

#[tauri::command]
fn resume_session(capture_id: String, include_loopback: bool, include_microphone: bool) -> Result<serde_json::Value, String> {
    let mut args = vec!["session", "resume", "--capture-id", capture_id.as_str()];
    if !include_loopback {
        args.push("--no-loopback");
    }
    if !include_microphone {
        args.push("--no-microphone");
    }
    run_backend_json(&args)
}

#[tauri::command]
fn stop_session(capture_id: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "record-stop", "--capture-id", capture_id.as_str()])
}

#[tauri::command]
fn set_keep_source_audio(capture_id: String, enabled: bool) -> Result<serde_json::Value, String> {
    run_backend_json(&[
        "session",
        "keep-audio",
        "--capture-id",
        capture_id.as_str(),
        "--enabled",
        if enabled { "true" } else { "false" },
    ])
}

#[tauri::command]
fn delete_source_audio(capture_id: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "delete-audio", "--capture-id", capture_id.as_str()])
}

#[tauri::command]
fn archive_session(capture_id: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "archive", "--capture-id", capture_id.as_str()])
}

#[tauri::command]
fn load_retention_settings() -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "retention-show"])
}

#[tauri::command]
fn save_retention_settings(raw_audio_retention_days: i64, delete_temp_processing_files: bool) -> Result<serde_json::Value, String> {
    let raw_days = raw_audio_retention_days.to_string();
    run_backend_json(&[
        "session",
        "retention-update",
        "--raw-audio-retention-days",
        raw_days.as_str(),
        "--delete-temp-processing-files",
        if delete_temp_processing_files { "true" } else { "false" },
    ])
}

#[tauri::command]
fn cleanup_retention() -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "cleanup"])
}

#[tauri::command]
fn finalise_session(capture_id: String) -> Result<serde_json::Value, String> {
    run_backend_json(&["session", "finalise", "--capture-id", capture_id.as_str()])
}

#[tauri::command]
fn list_action_tracker_items(limit: Option<i64>, filter: Option<String>, sort: Option<String>) -> Result<serde_json::Value, String> {
    let limit_arg = limit.unwrap_or(200).clamp(1, 500).to_string();
    let filter_value = filter.unwrap_or_else(|| "active".to_string());
    let sort_value = sort.unwrap_or_else(|| "recent".to_string());
    run_backend_json(&[
        "actions",
        "workspace",
        "--limit",
        limit_arg.as_str(),
        "--filter",
        filter_value.as_str(),
        "--sort",
        sort_value.as_str(),
    ])
}

#[tauri::command]
fn update_action_workflow(item_type: String, item_id: i64, workflow_status: String, due_at: Option<String>, notes: Option<String>) -> Result<serde_json::Value, String> {
    let item_id_arg = item_id.to_string();
    let mut args = vec![
        "actions",
        "update-workflow",
        "--item-type",
        item_type.as_str(),
        "--item-id",
        item_id_arg.as_str(),
        "--workflow-status",
        workflow_status.as_str(),
    ];
    if let Some(value) = due_at.as_deref() {
        args.push("--due-at");
        args.push(value);
    }
    if let Some(value) = notes.as_deref() {
        args.push("--notes");
        args.push(value);
    }
    run_backend_json(&args)
}

#[tauri::command]
fn list_memory_items(item_type: String, limit: Option<i64>) -> Result<serde_json::Value, String> {
    let limit_arg = limit.unwrap_or(200).clamp(1, 500).to_string();
    run_backend_json(&["memory", "list", "--item-type", item_type.as_str(), "--limit", limit_arg.as_str()])
}

#[tauri::command]
fn save_review_item(
    item_type: String,
    item_id: i64,
    review_status: String,
    description: Option<String>,
    owner_name: Option<String>,
) -> Result<serde_json::Value, String> {
    let item_id_arg = item_id.to_string();
    let mut args = vec![
        "review",
        "update-item",
        "--item-type",
        item_type.as_str(),
        "--item-id",
        item_id_arg.as_str(),
        "--review-status",
        review_status.as_str(),
    ];
    if let Some(value) = description.as_deref() {
        args.push("--description");
        args.push(value);
    }
    if let Some(value) = owner_name.as_deref() {
        args.push("--owner-name");
        args.push(value);
    }

    run_backend_json(&args)
}

fn run_backend(args: &[&str]) -> Result<String, String> {
    let project_root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .ok_or_else(|| "Unable to resolve project root.".to_string())?;
    let venv_python = project_root.join(".venv").join("Scripts").join("python.exe");
    let python = if venv_python.exists() {
        venv_python
    } else {
        std::path::PathBuf::from("python")
    };

    let mut command = std::process::Command::new(python);
    command
        .current_dir(project_root)
        .env("PYTHONPATH", project_root.join("backend").join("src"))
        .arg("-m")
        .arg("local_meeting_notes.app")
        .args(args);

    let output = command
        .output()
        .map_err(|error| format!("Failed to run backend: {error}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        return Err(if stderr.is_empty() { stdout } else { stderr });
    }
    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

fn run_backend_json(args: &[&str]) -> Result<serde_json::Value, String> {
    let output = run_backend(args)?;
    serde_json::from_str(&output).map_err(|error| format!("Invalid backend JSON: {error}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            scaffold_status,
            session_dashboard,
            create_session,
            create_planned_session,
            list_planned_sessions,
            list_upcoming_sessions,
            create_session_from_upcoming,
            get_session,
            rename_session,
            start_session,
            pause_session,
            resume_session,
            stop_session,
            set_keep_source_audio,
            delete_source_audio,
            archive_session,
            load_retention_settings,
            save_retention_settings,
            cleanup_retention,
            review_capture,
            list_recent_captures,
            session_library,
            session_search,
            export_capture,
            finalise_session,
            list_action_tracker_items,
            update_action_workflow,
            list_memory_items,
            save_review_item
        ])
        .run(tauri::generate_context!())
        .expect("error while running Local Meeting Notes");
}
