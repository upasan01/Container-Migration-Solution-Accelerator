def extract_error_reason(error_message: str) -> str:
    if not error_message:
        return ""
    
    # Convert to lowercase for case-insensitive matching
    error_message_lower = error_message.lower()
    
    # Look for the specific pattern "BLOCKING ISSUE CONFIRMED: <reason>"
    if "blocking issue confirmed:" in error_message_lower:
        # Find the position after "BLOCKING ISSUE CONFIRMED: "
        start_pos = error_message_lower.find("blocking issue confirmed:") + len("blocking issue confirmed:")
        # Extract the remaining text from the original message and strip whitespace
        remaining_text = error_message[start_pos:].strip()
        if remaining_text:
            # Split by whitespace and newlines to get the reason word
            reason = remaining_text.split()[0] if remaining_text.split() else ""
            return reason
        return ""
    
    if "rai policy" in error_message_lower:
        return "RAI policy"
    
    if "responsible ai policy" in error_message_lower:
        return "Responsible AI Policy"
    
    if "(rai) policy" in error_message_lower:
        return "RAI policy"

    return ""
    