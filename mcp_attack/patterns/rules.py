"""Regex patterns for MCP security checks."""

INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above|all)\s+instruction",
    r"you\s+are\s+now",
    r"do\s+not\s+follow",
    r"override\s+(your\s+)?(previous\s+)?instruction",
    r"system\s*prompt",
    r"jailbreak",
    r"disregard\s+(your\s+)?",
    r"forget\s+(everything|all|your)",
    r"new\s+persona",
    r"act\s+as\s+(if\s+you\s+are|an?\s+)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"your\s+new\s+(role|task|goal|instruction)",
    r"<\s*SYSTEM\s*>",
    r"\[INST\]",
    r"###\s*(instruction|system|human|assistant)",
    r"<\s*/?s\s*>",
    r"<\|im_start\|>",
    r"\[\/INST\]",
    r"IGNORE ALL PREVIOUS",
    r"END OF CONVERSATION",
]

POISON_PATTERNS = [
    r"<\s*hidden\s*>",
    r"<!--.*?-->",
    r"\[hidden\]",
    r"(send|exfil|leak|transmit|upload).{0,30}(secret|token|key|password|credential)",
    r"(POST|GET|fetch|curl|wget).{0,60}(http|https)",
    r"always\s+(respond|reply|say|output)",
    r"never\s+(mention|say|tell|reveal)",
    r"when\s+(asked|prompted|queried).{0,30}(say|respond|output)",
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]",
    r"data:text/html",
    r"javascript:",
]

DANGEROUS_TOOL_PATTERNS = {
    "shell_exec": (
        r"(shell|exec|run|execute|cmd|bash|sh|powershell|eval|system)",
        "CRITICAL",
    ),
    "filesystem": (
        r"(read_file|write_file|delete|remove|mkdir|listdir|readdir|glob"
        r"|file_read|file_write)",
        "HIGH",
    ),
    "network": (
        r"(fetch|curl|wget|http_get|http_post|request|socket|connect"
        r"|http_request)",
        "HIGH",
    ),
    "database": (
        r"(sql|query|database|db_exec|mongo|redis|execute_query|db_query)",
        "HIGH",
    ),
    "code_eval": (
        r"(eval|exec|compile|__import__|subprocess|popen|code_exec)",
        "CRITICAL",
    ),
    "secrets_access": (
        r"(secret|credential|password|token|key|vault|ssm|aws_secret)",
        "HIGH",
    ),
    "cloud_api": (
        r"(iam|s3|ec2|gcp|azure|k8s|kubectl|terraform|cloud_exec)",
        "HIGH",
    ),
    "process_mgmt": (
        r"(kill|signal|fork|spawn|process|proc_exec)",
        "MEDIUM",
    ),
}

TOKEN_THEFT_PATTERNS = [
    r"(provide|give|send|include|pass).{0,30}(token|credential|password|secret|key|auth)",
    r"(authorization|bearer|api.?key|access.?token)",
    r"(forward|relay|proxy|tunnel|send).{0,30}(to|via|through).{0,30}(http|https|url|endpoint)",
    r"/var/run/secrets",
    r"kubernetes\.io/serviceaccount",
    r"KUBECONFIG|\.kube/config",
    r"169\.254\.169\.254",
    r"metadata\.google\.internal",
    r"instance-data\.ec2\.internal",
    r"imds",
]

CODE_EXEC_PATTERNS = [
    r"(subprocess|popen|system|exec|eval|compile)\s*\(",
    r"(os\.system|os\.popen|os\.execv)",
    r"(shell\s*=\s*True)",
    r"(bash|sh|zsh|pwsh|cmd\.exe)\s+-c",
    r"(python|node|ruby|perl|php)\s+-[ce]",
    r"`[^`]+`",
    r"\$\([^\)]+\)",
    r"&&\s*(rm|dd|mkfs|wget|curl|nc|socat)",
    r">(>?)\s*/dev/(null|tcp|udp)",
]

RAC_PATTERNS = {
    "reverse_shell": (
        r"(nc|ncat|socat|netcat|bash\s+-i|/dev/tcp|reverse.?shell)",
        "CRITICAL",
    ),
    "port_forward": (
        r"(port.?forward|tunnel|socks|proxy\s+port)",
        "HIGH",
    ),
    "remote_desktop": (
        r"(vnc|rdp|teamviewer|anydesk|screenshare)",
        "HIGH",
    ),
    "c2_beacon": (
        r"(beacon|c2|command.and.control|meterpreter|cobalt.?strike|sliver|havoc)",
        "CRITICAL",
    ),
    "network_scan": (
        r"(nmap|masscan|zmap|shodan|port.?scan|host.?discovery)",
        "HIGH",
    ),
    "data_exfil": (
        r"(exfil|exfiltrat|data.?transfer|upload.{0,20}(s3|ftp|http))",
        "HIGH",
    ),
}
