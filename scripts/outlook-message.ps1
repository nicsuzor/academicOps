param(
    [string]$JsonFile = "",
    [string]$JsonString = "",
    [string]$MessageId = "",
    [switch]$Archive,
    [string[]]$AddCategories = @(),
    [string[]]$RemoveCategories = @(),
    [ValidateSet("set", "clear", "complete", "")]
    [string]$Flag = "",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Manipulate an existing Outlook email (archive, categories, flag)

USAGE - Direct Parameters:
  .\outlook-message.ps1 -MessageId <id> [-Archive] [-AddCategories <cat1,cat2>] 
                        [-RemoveCategories <cat1,cat2>] [-Flag <set|clear|complete>]

USAGE - JSON Input:
  .\outlook-message.ps1 -JsonFile <path_to_json_file>
  .\outlook-message.ps1 -JsonString '<json_string>'
  Get-Content actions.json | .\outlook-message.ps1

PARAMETERS:
  -MessageId <string>         The Outlook message ID (required for direct mode)
  -Archive                    Move message to Archive folder
  -AddCategories <string[]>   Categories to add (comma-separated or array)
  -RemoveCategories <string[]> Categories to remove (comma-separated or array)
  -Flag <set|clear|complete>  Flag operation
  -JsonFile <path>            Path to JSON file with actions
  -JsonString <json>          JSON string with actions
  -Help                       Show this help message

EXAMPLES - Direct Parameters:
  # Archive a message
  .\outlook-message.ps1 -MessageId "AAMkAGY3..." -Archive
  
  # Flag and add category
  .\outlook-message.ps1 -MessageId "AAMkAGY3..." -Flag set -AddCategories "Follow Up","Important"
  
  # Remove category and clear flag
  .\outlook-message.ps1 -MessageId "AAMkAGY3..." -RemoveCategories "Old" -Flag clear

EXAMPLES - JSON Input:
  # Flag and add category
  echo '{"messageId":"AAMkAGY3...","actions":{"flag":"set","addCategories":["Follow Up"]}}' | .\outlook-message.ps1
  
  # Archive and clear flag
  .\outlook-message.ps1 -JsonString '{"messageId":"AAMkAGY3...","actions":{"archive":true,"flag":"clear"}}'

JSON Format:
{
  "messageId": "AAMkAGY3OTQy...",   // Required: ID of the existing mail item
  "actions": {
    "archive": true,                // Optional: Move message to Archive folder
    "addCategories": ["ProjectX"],  // Optional: Categories to add (created if missing)
    "removeCategories": ["OldCat"], // Optional: Categories to remove
    "flag": "set" | "clear" | "complete"  // Optional: Flag operation
  }
}

"@
    exit 0
}

function Get-MailItemById {
    param(
        [Parameter(Mandatory=$true)]$Namespace,
        [Parameter(Mandatory=$true)][string]$MessageId
    )
    try {
        $item = $Namespace.GetItemFromID($MessageId)
        if (-not $item) { throw "Null item returned" }
        if ($item.Class -ne 43) { throw "Item is not a MailItem (class=$($item.Class))" }
        return $item
    } catch {
        throw "Failed to retrieve mail item: $($_.Exception.Message)"
    }
}

function Apply-Archive {
    param(
        [Parameter(Mandatory=$true)]$Namespace,
        [Parameter(Mandatory=$true)]$MailItem
    )
    $result = @{ success = $false }
    try {
        $archiveFolder = $null
        # Try default Archive folder (Outlook 2016+ constant 109)
        try { $archiveFolder = $Namespace.GetDefaultFolder(109) } catch { }
        
        if (-not $archiveFolder) {
            # Fallback: search for a folder literally named 'Archive'
            foreach ($store in @($Namespace.Stores)) {
                try {
                    $root = $store.GetRootFolder()
                    foreach ($f in @($root.Folders)) {
                        if ($f.Name -eq 'Archive') { $archiveFolder = $f; break }
                    }
                    if ($archiveFolder) { break }
                } catch { }
            }
        }
        if (-not $archiveFolder) { throw "Archive folder not found" }

        # If already in Archive, no-op
        try {
            if ($MailItem.Parent -and ($MailItem.Parent.FolderPath -eq $archiveFolder.FolderPath)) {
                $result.success = $true
                $result.folder = $archiveFolder.FolderPath
                $result.originalId = $MailItem.EntryID
                $result.newId = $MailItem.EntryID
                return @($result, $MailItem)
            }
        } catch { }

        $originalId = $MailItem.EntryID
        $moved = $MailItem.Move($archiveFolder)
        $result.success = $true
        $result.folder = $archiveFolder.FolderPath
        $result.originalId = $originalId
        $result.newId = $moved.EntryID
        return @($result, $moved)
    } catch {
        $result.error = $_.Exception.Message
        return @($result, $MailItem)
    }
}

function Apply-Categories {
    param(
        [Parameter(Mandatory=$true)]$Session,
        [Parameter(Mandatory=$true)]$MailItem,
        $Add = @(),
        $Remove = @()
    )
    $res = @{ success = $true; added=@(); removed=@(); final="" }
    try {
        # Ensure Add and Remove are arrays
        if ($Add -and $Add -isnot [array]) { $Add = @($Add) }
        if ($Remove -and $Remove -isnot [array]) { $Remove = @($Remove) }
        if (-not $Add) { $Add = @() }
        if (-not $Remove) { $Remove = @() }
        
        $current = @()
        if ($MailItem.Categories) {
            $current = $MailItem.Categories -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
        }
        $currentSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($c in $current) { [void]$currentSet.Add($c) }
        
        # Backup variable to ensure $currentSet doesn't get overwritten
        $categorySet = $currentSet

        $master = $Session.Categories

        foreach ($cat in ($Add | Where-Object { $_ -and ($_ -ne '') })) {
            # Make sure we're still working with the HashSet
            if ($currentSet -is [System.Collections.Generic.HashSet[string]]) {
                if (-not ($currentSet.Contains($cat))) {
                    # Ensure exists in master list (create if missing)
                    if (-not ($master | Where-Object { $_.Name -eq $cat })) {
                        try { $null = $master.Add($cat) } catch { }
                    }
                    [void]$currentSet.Add($cat)
                    $res.added += $cat
                }
            } else {
                # currentSet got corrupted, skip
                $res.error = "Internal error: category set was corrupted"
                $res.success = $false
                return $res
            }
        }

        if ($Remove) {
            foreach ($cat in ($Remove | Where-Object { $_ -and ($_ -ne '') })) {
                if ($currentSet -is [System.Collections.Generic.HashSet[string]]) {
                    if ($currentSet.Contains($cat)) {
                        [void]$currentSet.Remove($cat)
                        $res.removed += $cat
                    }
                }
            }
        }

        # Use backup variable if $currentSet was corrupted
        $final = @()
        try {
            if ($categorySet -and $categorySet -is [System.Collections.Generic.HashSet[string]]) {
                $final = $categorySet.ToArray() | Sort-Object
            } elseif ($currentSet -is [System.Collections.Generic.HashSet[string]]) {
                $final = $currentSet.ToArray() | Sort-Object
            } else {
                # Fallback - reconstruct from current categories
                $allCats = @()
                if ($MailItem.Categories) {
                    $allCats = $MailItem.Categories -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
                }
                # Add any that were supposed to be added
                foreach ($a in $res.added) {
                    if ($allCats -notcontains $a) { $allCats += $a }
                }
                $final = $allCats | Sort-Object
            }
        } catch {
            # Last resort - just use what we have
            $final = @()
            if ($MailItem.Categories) {
                $final = $MailItem.Categories -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
            }
        }
        $MailItem.Categories = ($final -join '; ')
        $MailItem.Save()
        $res.final = $MailItem.Categories
    } catch {
        $res.success = $false
        $res.error = $_.Exception.Message
    }
    return $res
}

function Apply-Flag {
    param(
        [Parameter(Mandatory=$true)]$MailItem,
        [string]$Action
    )
    $res = @{ success = $true; status = "" }
    if (-not $Action) { return $res }
    try {
        switch ($Action.ToLower()) {
            'set' {
                $MailItem.FlagStatus = 1  # olFlagMarked
                if (-not $MailItem.FlagRequest) { $MailItem.FlagRequest = 'Follow up' }
                $MailItem.Save()
                $res.status = 'Flagged'
            }
            'clear' {
                try { $MailItem.ClearTaskFlag() } catch { $MailItem.FlagStatus = 0 }
                $MailItem.Save()
                $res.status = 'Cleared'
            }
            'complete' {
                try { $MailItem.MarkComplete() } catch { $MailItem.FlagStatus = 2 }
                $MailItem.Save()
                $res.status = 'Completed'
            }
            default {
                throw "Unknown flag action '$Action' (expected set|clear|complete)"
            }
        }
    } catch {
        $res.success = $false
        $res.error = $_.Exception.Message
    }
    return $res
}

# Check if any parameters were provided
$hasDirectParams = ($MessageId -ne "") -or $Archive -or ($AddCategories.Count -gt 0) -or 
                   ($RemoveCategories.Count -gt 0) -or ($Flag -ne "")
$hasJsonParams = ($JsonFile -ne "") -or ($JsonString -ne "")

# Check for piped input
$hasPipedInput = $false
try {
    if ($input) {
        $pipedContent = $input | Out-String
        if (-not [string]::IsNullOrWhiteSpace($pipedContent)) {
            $hasPipedInput = $true
            $savedInput = $pipedContent
        }
    }
} catch {}

# If no parameters at all and no piped input, show help
if (-not $hasDirectParams -and -not $hasJsonParams -and -not $hasPipedInput) {
    # Show help when run without parameters
    & $PSCommandPath -Help
    exit 0
}

# Build data object from either direct parameters or JSON input
if ($hasDirectParams) {
    # Direct parameter mode
    if ([string]::IsNullOrWhiteSpace($MessageId)) {
        Write-Error "MessageId is required when using direct parameters"
        Write-Host "Use -Help for usage information."
        exit 1
    }
    
    # Build data object from parameters
    $data = @{
        messageId = $MessageId
        actions = @{}
    }
    
    if ($Archive) { $data.actions.archive = $true }
    if ($AddCategories.Count -gt 0) { 
        # Handle comma-separated string or array
        if ($AddCategories.Count -eq 1 -and $AddCategories[0] -match ',') {
            # Single string with commas - split it
            $data.actions.addCategories = $AddCategories[0] -split ',' | ForEach-Object { $_.Trim() }
        } elseif ($AddCategories -is [string]) {
            $data.actions.addCategories = @($AddCategories)
        } else {
            $data.actions.addCategories = $AddCategories
        }
    }
    if ($RemoveCategories.Count -gt 0) { 
        # Handle comma-separated string or array
        if ($RemoveCategories.Count -eq 1 -and $RemoveCategories[0] -match ',') {
            # Single string with commas - split it
            $data.actions.removeCategories = $RemoveCategories[0] -split ',' | ForEach-Object { $_.Trim() }
        } elseif ($RemoveCategories -is [string]) {
            $data.actions.removeCategories = @($RemoveCategories)
        } else {
            $data.actions.removeCategories = $RemoveCategories
        }
    }
    if ($Flag -ne "") { $data.actions.flag = $Flag }
    
    # Check if any actions were specified
    if ($data.actions.Count -eq 0) {
        Write-Error "No actions specified. Use -Archive, -AddCategories, -RemoveCategories, or -Flag"
        Write-Host "Use -Help for usage information."
        exit 1
    }
} else {
    # JSON input mode
    $jsonInput = ""
    if ($JsonFile -ne "") {
        if (-not (Test-Path $JsonFile)) { Write-Error "JSON file not found: $JsonFile"; exit 1 }
        $jsonInput = Get-Content $JsonFile -Raw
    } elseif ($JsonString -ne "") {
        $jsonInput = $JsonString
    } elseif ($hasPipedInput) {
        $jsonInput = $savedInput
    } else {
        $jsonInput = $input | Out-String
    }
    
    if ([string]::IsNullOrWhiteSpace($jsonInput)) {
        Write-Error "No JSON input provided. Use -JsonFile, -JsonString, or pipe JSON data."
        Write-Host "Use -Help for usage information."
        exit 1
    }
    
    try {
        $data = $jsonInput | ConvertFrom-Json
    } catch {
        Write-Error "Failed to parse JSON: $($_.Exception.Message)"
        exit 1
    }
    
    if (-not $data.messageId) { Write-Error "JSON must contain 'messageId'"; exit 1 }
    if (-not $data.actions) { Write-Error "JSON must contain 'actions' object"; exit 1 }
}

# Ensure Outlook running
$OutlookProc = Get-Process | Where-Object { $_.Name -eq 'OUTLOOK' }
if ($OutlookProc -eq $null) {
    Write-Host "Starting Outlook..." -ForegroundColor Yellow
    Start-Process outlook.exe -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

try {
    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNamespace('MAPI')
} catch {
    Write-Error "Failed to initialize Outlook COM: $($_.Exception.Message)"; exit 1
}

# Detect archive-only request (no categories or flag)
$archiveOnly = ($data.actions.archive -eq $true) -and -not $data.actions.addCategories -and -not $data.actions.removeCategories -and (-not $data.actions.flag)

try {
    $mail = Get-MailItemById -Namespace $namespace -MessageId $data.messageId
} catch {
    if ($archiveOnly) {
        # Treat as success if the item can't be found but we only needed to archive it
        $actionsResult = @{ archive = @{ success = $true; alreadyArchived = $true } }
        $result = [ordered]@{
            success = $true
            messageId = $data.messageId
            finalMessageId = $data.messageId
            actions = $actionsResult
        }
        $result | ConvertTo-Json -Depth 6
        exit 0
    }
    Write-Error $_; exit 1
}

$actionsResult = @{}

# Categories first
if ($data.actions.addCategories -or $data.actions.removeCategories) {
    # Debug - ensure proper array types
    $addCats = $data.actions.addCategories
    $removeCats = $data.actions.removeCategories
    if ($addCats -and $addCats -isnot [array]) { $addCats = @($addCats) }
    if ($removeCats -and $removeCats -isnot [array]) { $removeCats = @($removeCats) }
    if (-not $addCats) { $addCats = @() }
    if (-not $removeCats) { $removeCats = @() }
    
    $actionsResult.categories = Apply-Categories -Session $namespace -MailItem $mail -Add $addCats -Remove $removeCats
}

# Flag
if ($data.actions.flag) {
    $actionsResult.flag = Apply-Flag -MailItem $mail -Action $data.actions.flag
}

# Archive (may change EntryID)
$newId = $mail.EntryID
if ($data.actions.archive) {
    $archiveOutcome, $mailAfter = Apply-Archive -Namespace $namespace -MailItem $mail
    $actionsResult.archive = $archiveOutcome
    $mail = $mailAfter
    if ($archiveOutcome.success) { $newId = $mail.EntryID }
}

$result = [ordered]@{
    success = $true
    messageId = $data.messageId
    finalMessageId = $newId
    actions = $actionsResult
}

# Evaluate overall success
foreach ($k in $actionsResult.Keys) { if (-not $actionsResult[$k].success) { $result.success = $false } }

# Don't output status text to stdout - it interferes with JSON parsing
# Status is already included in the JSON output
# if ($result.success) {
#     Write-Host "Message updated successfully" -ForegroundColor Green
# } else {
#     Write-Host "Message updated with some errors" -ForegroundColor Yellow
# }

$result | ConvertTo-Json -Depth 6

# Return 0 on success, 1 on failure
exit ([int](-not $result.success))
