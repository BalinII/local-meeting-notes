#[tauri::command]
fn scaffold_status() -> &'static str {
    "Local Meeting Notes Tauri scaffold is ready."
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![scaffold_status])
        .run(tauri::generate_context!())
        .expect("error while running Local Meeting Notes");
}
