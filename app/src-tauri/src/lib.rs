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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            scaffold_status,
            review_capture,
            export_capture
        ])
        .run(tauri::generate_context!())
        .expect("error while running Local Meeting Notes");
}
