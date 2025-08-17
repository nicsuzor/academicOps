param(
    # List parameters
    [int]$PageSize = 20,
    [int]$PageNumber = 1,
    [switch]$UnreadOnly = $false,
    [switch]$ShowTotal = $false,

    # Detail parameters
    [string]$GetEmailById = "",
    [switch]$GetLastMessageInConversation = $false,
    [switch]$IncludeAttachmentContent = $false,
    [switch]$Raw = $false,  # Fetch additional (structured) fields
    [int]$MaxAttachmentSize = 1048576,  # 1MB default limit for content

    # Help
    [switch]$Help
)

# Force UTF-8 output so piping from Windows PowerShell (UTF-16LE by default) into WSL tools like jq works.
try {
    if ($PSVersionTable.PSEdition -eq 'Desktop') {  # Windows PowerShell
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
    }
} catch { }

if ($Help) {
    Write-Host @"
Outlook email listing and detailed email fetching

Usage: 
  # List emails
  outlook-read.ps1 [-PageSize <num>] [-PageNumber <num>] [-UnreadOnly] [-ShowTotal]
  
  # Get a specific email
  outlook-read.ps1 -GetEmailById <email_id> [-IncludeAttachmentContent] [-MaxAttachmentSize <bytes>]

  # Get the newest email in a conversation thread
  outlook-read.ps1 -GetEmailById <email_id> -GetLastMessageInConversation

List Parameters:
  -PageSize         Number of emails per page (default: 20)
  -PageNumber       Page number to retrieve (default: 1)
  -UnreadOnly       Only show unread emails
  -ShowTotal        Include total count in output metadata

Detail Parameters:
  -GetEmailById                   Fetch full details for a specific email by ID
  -Raw                            Fetch the raw email without JSON formatting
  -GetLastMessageInConversation   Fetch the most recent email in the conversation thread of the given ID
  -IncludeAttachmentContent       Include attachment content as base64 (default: metadata only)
  -MaxAttachmentSize              Max attachment size for content (default: 1MB)

Examples:
  outlook-read.ps1                                                 # List emails with a body snippet
  outlook-read.ps1 -GetEmailById "AAMkAGY3OTQy..."                 # Get a specific full email
  outlook-read.ps1 -GetEmailById "..." -GetLastMessageInConversation # Get the latest reply in a thread
"@
    exit 0
}


function Sanitize-Text {
    param([string]$Text)
    if ($null -eq $Text) { return $null }
    # Strip control chars except TAB (0x09) LF (0x0A) CR (0x0D)
    $clean = $Text -replace '[\x00-\x08\x0B\x0C\x0E-\x1F]', ''
    # Normalize CRLF -> LF (JSON friendly / consistent)
    $clean = $clean -replace "`r`n", "`n"
    return $clean
}

function Format-ShortID {
    param([string]$EntryID)
    if ($null -eq $EntryID -or $EntryID.Length -lt 12) { return $EntryID }
    # Take last 8 chars which are usually unique enough for display
    return "..." + $EntryID.Substring($EntryID.Length - 8)
}

function Format-SenderDisplay {
    param([string]$SenderAddress)
    if ($null -eq $SenderAddress) { return "" }
    
    # Handle Exchange/LDAP format
    if ($SenderAddress -match '/CN=RECIPIENTS/CN=([^-]+)-(.+)$') {
        # Extract the username part (after the last dash)
        return $matches[2]
    } elseif ($SenderAddress -match '/CN=([^/]+)$') {
        # Fallback pattern
        return ""
    } elseif ($SenderAddress -match '@') {
        # Regular email - return as is
        return $SenderAddress
    } else {
        # Unknown format - truncate if too long
        if ($SenderAddress.Length -gt 30) {
            return $SenderAddress.Substring(0, 27) + "..."
        }
        return $SenderAddress
    }
}

function Convert-MailItem {
    param(
        [Parameter(Mandatory)]
        $MailItem,
        [switch]$Raw,
        [switch]$IncludeAttachmentContent,
        [int]$MaxAttachmentSize = 1048576,
        [string[]]$ExcludeRawProperties
    )

    # Default exclusions for Raw mode (large / binary / redundant / COM graph roots)
    $defaultRawExcludes = @(
        'RTFBody',          # Large binary
        'Actions',
        'Application',
        'AttachmentSelection',
        'Attachments',      # We map separately
        'BillingInformation',
        'Categories',       # Often empty; retain if you want
        'DownloadState',
        'FormDescription',
        'GetInspector',
        'ItemProperties',
        'MAPIOBJECT',
        'Parent',
        'PropertyAccessor', # Requires explicit DASL querying
        'ReplyRecipients',  # Covered via Recipients
        'Recipients',       # We expand already
        'Save',
        'Session',
        'UnRead'            # We expose isRead already
    )

    if ($ExcludeRawProperties) {
        # Merge user exclusions (case-insensitive)
        $defaultRawExcludes = ($defaultRawExcludes + $ExcludeRawProperties) | Select-Object -Unique
    }

    # Base (legacy) structure
    $bodyPlain = Sanitize-Text $MailItem.Body
    $bodyHtml  = Sanitize-Text $MailItem.HTMLBody
    $obj = [ordered]@{
        id                 = $MailItem.EntryID
        subject            = $MailItem.Subject
        # Use sanitized versions so embedded quotes and control chars are safely handled by ConvertTo-Json
        body               = $bodyPlain
        # bodyHTML           = $bodyHtml
        # bodyFormat         = switch ($MailItem.BodyFormat) {
        #     1 { "PlainText" } 2 { "HTML" } 3 { "RichText" } default { "Unknown" }
        # }
        receivedTime       = $MailItem.ReceivedTime.ToString("yyyy-MM-dd HH:mm:ss")
        senderEmailAddress = Format-SenderDisplay $MailItem.SenderEmailAddress
        senderName         = $MailItem.SenderName
        to                 = $MailItem.To
        cc                 = $MailItem.CC
        isRead             = -not $MailItem.UnRead
        hasAttachments     = $MailItem.Attachments.Count -gt 0
        size               = $MailItem.Size
        conversationID     = $MailItem.ConversationID
        attachments        = @()
    }

    foreach ($attachment in $MailItem.Attachments) {
        $att = @{
            fileName   = $attachment.FileName
            size       = $attachment.Size
            isEmbedded = $attachment.Position -ge 0
        }
        if ($IncludeAttachmentContent -and $attachment.Type -eq 1 -and $attachment.Size -le $MaxAttachmentSize) {
            try {
                $tmp = [System.IO.Path]::GetTempFileName()
                $attachment.SaveAsFile($tmp)
                $bytes = [System.IO.File]::ReadAllBytes($tmp)
                $att.contentBase64 = [Convert]::ToBase64String($bytes)
                Remove-Item $tmp -ErrorAction SilentlyContinue
            } catch {
                $att.contentError = $_.Exception.Message
            }
        }
        $obj.attachments += $att
    }

    if (-not $Raw) {
        return [pscustomobject]$obj
    }

    # Raw: include extra scalar-ish MailItem properties minus exclusions
    $allProps   = [ordered]@{}
    $propNames  = ($MailItem | Get-Member -MemberType Property | Select-Object -ExpandProperty Name)
    $excludesCI = New-Object System.Collections.Generic.HashSet[string] ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($n in $defaultRawExcludes) { [void]$excludesCI.Add($n) }

    foreach ($name in $propNames | Sort-Object) {
        if ($excludesCI.Contains($name)) { continue }
        if ($allProps.Contains($name)) { continue }
        try {
            $value = $MailItem.$name
            if ($null -eq $value) { $allProps[$name] = $null; continue }

            if ([System.Runtime.InteropServices.Marshal]::IsComObject($value)) {
                # Skip nested COM graphs
                continue
            }

            if ($value -is [string] -or
                $value -is [int] -or
                $value -is [long] -or
                $value -is [double] -or
                $value -is [decimal] -or
                $value -is [bool] -or
                $value -is [datetime]) {
                $allProps[$name] = $value
                continue
            }

            if ($value -is [System.Collections.IEnumerable] -and -not ($value -is [string])) {
                # Materialize simple enumerables
                $allProps[$name] = @($value)
                continue
            }

            # Fallback
            $allProps[$name] = $value.ToString()
        } catch {
            # Ignore unreadable property
        }
    }

    $obj.AllProperties = $allProps
    return [pscustomobject]$obj
}

function Get-FullEmail {
    param(
        [Parameter(Mandatory=$true)] $Namespace,
        [Parameter(Mandatory=$true)] [string]$EmailId,
        [bool]$IncludeContent = $false,
        [int]$MaxSize = 1048576,
        [bool]$GetLastInConversation = $false,
        [bool]$Raw = $false
    )

    try {
        $initial = $Namespace.GetItemFromID($EmailId)
        $target = $initial
        if ($GetLastInConversation) {
            $conv = $initial.GetConversation()
            if ($conv) {
                $table = $conv.GetTable()
                $table.Sort("[ReceivedTime]", $true)
                $latest = $table.GetLast()
                if ($latest) {
                    $target = $Namespace.GetItemFromID($latest.EntryID)
                }
            }
        }
        if ($target.Class -ne 43) { throw "Item is not a mail message" }

        return Convert-MailItem -MailItem $target -Raw:$Raw -IncludeAttachmentContent:$IncludeContent -MaxAttachmentSize $MaxSize
    } catch {
        throw "Error retrieving email: $($_.Exception.Message)"
    }
}

try {
    # Ensure Outlook is running
    $OutlookProc = Get-Process | Where-Object { $_.Name -eq "OUTLOOK" }
    if ($OutlookProc -eq $null) {
        Start-Process outlook.exe -WindowStyle Hidden
        Start-Sleep -Seconds 5
    }

    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNamespace("MAPI")
    
    # Check if we're fetching a single email
    if ($GetEmailById -ne "") {   
        $fullEmail = Get-FullEmail -Namespace $namespace -EmailId $GetEmailById -Raw:$Raw -IncludeContent:$IncludeAttachmentContent -MaxSize $MaxAttachmentSize -GetLastInConversation:$GetLastMessageInConversation
        $jsonDepth = if ($Raw) { 6 } else { 4 }
        $fullEmail | ConvertTo-Json -Depth $jsonDepth
        exit 0
    }
    
    # List mode
    $inbox = $namespace.GetDefaultFolder(6) # olFolderInbox
    $items = $inbox.Items
    $items.Sort("[ReceivedTime]", $true)
    
    if ($UnreadOnly) {
        $items = $items.Restrict("[UnRead] = True")
    }
    
    $totalCount = $items.Count
    $totalPages = [Math]::Ceiling($totalCount / $PageSize)
    
    $startIndex = ($PageNumber - 1) * $PageSize + 1
    $endIndex = [Math]::Min($startIndex + $PageSize - 1, $totalCount)
    
    $emailList = @()
    
    for ($i = $startIndex; $i -le $endIndex; $i++) {
        $email = $items.Item($i)
        
        if ($email.Class -eq 43) { # olMail
        
            $emailObj = @{
                id = $email.EntryID
                shortId = Format-ShortID $email.EntryID
                date = $email.ReceivedTime.ToString("yyyy-MM-dd HH:mm:ss")
                sender = Format-SenderDisplay $email.SenderEmailAddress
                to = $email.To
                cc = $email.CC
                subject = $email.Subject
                isRead = -not $email.UnRead
                hasAttachments = $email.Attachments.Count -gt 0
                size = $email.Size
            }

            # Add snippet
            $bodyContent = Sanitize-Text $email.Body
            $snippetLength = [Math]::Min(400, $bodyContent.Length)
            $emailObj.snippet = $bodyContent.Substring(0, $snippetLength).Trim()

            $emailList += $emailObj
        }
    }
    
    $result = @{
        emails = $emailList
        paging = @{
            pageNumber = $PageNumber
            pageSize = $PageSize
            totalPages = $totalPages
        }
    }
    
    if ($ShowTotal) {
        $result.paging.totalCount = $totalCount
    }
    
    $result | ConvertTo-Json -Depth 3
    
} catch {
    Write-Error "Error accessing Outlook: $($_.Exception.Message)"
    exit 1
}