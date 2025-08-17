param(
    [string]$JsonFile = "",
    [string]$JsonString = "",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Save draft email response from JSON input

Usage: 
  .\outlook-draft.ps1 -JsonFile <path_to_json_file>
  .\outlook-draft.ps1 -JsonString '<json_string>'
  Get-Content draft.json | .\outlook-draft.ps1

JSON Format:
{
  "messageId": "AAMkAGY3OTQy...",  // Optional: Reply to this email ID
  "subject": "Email subject",      // Required for new emails, optional for replies
  "body": "Email body content",    // Required
  "bodyFormat": "HTML",            // Optional: "HTML" or "Text" (default: "Text")
  "recipients": {                  // Optional: Only for new emails (not replies)
    "to": ["email1@domain.com", "Name <email2@domain.com>"],
    "cc": ["email3@domain.com"],
    "bcc": ["email4@domain.com"]
  },
  "importance": "Normal",          // Optional: "Low", "Normal", "High"
  "requestReadReceipt": false,     // Optional: Boolean
  "requestDeliveryReceipt": false  // Optional: Boolean
}

Examples:
  # Reply to existing email
  echo '{"messageId":"AAMkAGY3...","body":"Thanks for your email!"}' | .\outlook-draft.ps1
  
  # New email
  echo '{"subject":"New Message","body":"Hello","recipients":{"to":["test@example.com"]}}' | .\outlook-draft.ps1
  
  # From file
  .\outlook-draft.ps1 -JsonFile "draft-response.json"
"@
    exit 0
}

function New-DraftEmail {
    param(
        [Parameter(Mandatory=$true)]
        $Outlook,
        [Parameter(Mandatory=$true)]
        $DraftData
    )
    
    try {
        # Create new mail item
        $draft = $Outlook.CreateItem(0)  # 0 = olMailItem
        
        # Set basic properties
        if ($DraftData.subject) {
            $draft.Subject = $DraftData.subject
        }
        
        if ($DraftData.body) {
            if ($DraftData.bodyFormat -eq "HTML") {
                $draft.HTMLBody = $DraftData.body
            } else {
                $draft.Body = $DraftData.body
            }
        }
        
        # Set importance
        if ($DraftData.importance) {
            switch ($DraftData.importance.ToLower()) {
                "low" { $draft.Importance = 0 }
                "normal" { $draft.Importance = 1 }
                "high" { $draft.Importance = 2 }
            }
        }
        
        # Set receipts
        if ($DraftData.requestReadReceipt) {
            $draft.ReadReceiptRequested = $true
        }
        if ($DraftData.requestDeliveryReceipt) {
            $draft.OriginatorDeliveryReportRequested = $true
        }
        
        # Add recipients
        if ($DraftData.recipients) {
            # To recipients
            if ($DraftData.recipients.to) {
                foreach ($recipient in $DraftData.recipients.to) {
                    $draft.Recipients.Add($recipient).Type = 1  # 1 = olTo
                }
            }
            
            # CC recipients
            if ($DraftData.recipients.cc) {
                foreach ($recipient in $DraftData.recipients.cc) {
                    $draft.Recipients.Add($recipient).Type = 2  # 2 = olCC
                }
            }
            
            # BCC recipients
            if ($DraftData.recipients.bcc) {
                foreach ($recipient in $DraftData.recipients.bcc) {
                    $draft.Recipients.Add($recipient).Type = 3  # 3 = olBCC
                }
            }
            
            # Resolve recipients
            $draft.Recipients.ResolveAll() | Out-Null
        }
        
        # Save as draft
        $draft.Save()
        
        return @{
            success = $true
            draftId = $draft.EntryID
            subject = $draft.Subject
            type = "new"
        }
        
    } catch {
        return @{
            success = $false
            error = "Failed to create new draft: $($_.Exception.Message)"
        }
    }
}

function New-ReplyDraft {
    param(
        [Parameter(Mandatory=$true)]
        $Namespace,
        [Parameter(Mandatory=$true)]
        [string]$OriginalMessageId,
        [Parameter(Mandatory=$true)]
        $DraftData
    )
    
    try {
        # Get original email
        $originalEmail = $Namespace.GetItemFromID($OriginalMessageId)
        
        if ($originalEmail.Class -ne 43) {
            throw "Original item is not a mail message"
        }
        
        # Create reply
        $reply = $originalEmail.Reply()
        
        # Set body content
        if ($DraftData.body) {
            if ($DraftData.bodyFormat -eq "HTML") {
                # For HTML replies, we need to preserve the original message
                $originalHtml = $reply.HTMLBody
                $newBody = $DraftData.body
                
                # Insert new content before original message
                if ($originalHtml -match "(<div[^>]*>.*?<div[^>]*>.*?</div>.*?</div>)") {
                    $reply.HTMLBody = $newBody + "<br><br>" + $originalHtml
                } else {
                    $reply.HTMLBody = $newBody + "<br><br>" + $originalHtml
                }
            } else {
                # For plain text, add before original content
                $reply.Body = $DraftData.body + "`n`n" + $reply.Body
            }
        }
        
        # Override subject if provided
        if ($DraftData.subject) {
            $reply.Subject = $DraftData.subject
        }
        
        # Set importance
        if ($DraftData.importance) {
            switch ($DraftData.importance.ToLower()) {
                "low" { $reply.Importance = 0 }
                "normal" { $reply.Importance = 1 }
                "high" { $reply.Importance = 2 }
            }
        }
        
        # Set receipts
        if ($DraftData.requestReadReceipt) {
            $reply.ReadReceiptRequested = $true
        }
        if ($DraftData.requestDeliveryReceipt) {
            $reply.OriginatorDeliveryReportRequested = $true
        }
        
        # Save as draft
        $reply.Save()
        
        return @{
            success = $true
            draftId = $reply.EntryID
            subject = $reply.Subject
            originalSubject = $originalEmail.Subject
            originalSender = $originalEmail.SenderName
            type = "reply"
        }
        
    } catch {
        return @{
            success = $false
            error = "Failed to create reply draft: $($_.Exception.Message)"
        }
    }
}

# Get JSON input
$jsonInput = ""

if ($JsonFile -ne "") {
    if (-not (Test-Path $JsonFile)) {
        Write-Error "JSON file not found: $JsonFile"
        exit 1
    }
    $jsonInput = Get-Content $JsonFile -Raw
} elseif ($JsonString -ne "") {
    $jsonInput = $JsonString
} else {
    # Read from pipeline/stdin
    $jsonInput = $input | Out-String
}

if ([string]::IsNullOrWhiteSpace($jsonInput)) {
    Write-Error "No JSON input provided. Use -JsonFile, -JsonString, or pipe JSON data."
    Write-Host "Use -Help for usage information."
    exit 1
}

try {
    # Parse JSON
    $draftData = $jsonInput | ConvertFrom-Json
    
    # Validate required fields
    if (-not $draftData.body) {
        Write-Error "JSON must contain 'body' field"
        exit 1
    }
    
    # Ensure Outlook is running
    $OutlookProc = Get-Process | Where-Object { $_.Name -eq "OUTLOOK" }
    if ($OutlookProc -eq $null) {
        Write-Host "Starting Outlook..." -ForegroundColor Yellow
        Start-Process outlook.exe -WindowStyle Hidden
        Start-Sleep -Seconds 5
    }

    # Create Outlook COM object
    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNamespace("MAPI")
    
    # Determine if this is a reply or new email
    if ($draftData.messageId) {
        Write-Host "Creating reply draft..." -ForegroundColor Yellow
        $result = New-ReplyDraft -Namespace $namespace -OriginalMessageId $draftData.messageId -DraftData $draftData
    } else {
        Write-Host "Creating new draft..." -ForegroundColor Yellow
        
        # Validate recipients for new emails
        if (-not $draftData.recipients -or -not $draftData.recipients.to) {
            Write-Error "New emails must have recipients.to field"
            exit 1
        }
        
        if (-not $draftData.subject) {
            Write-Error "New emails must have subject field"
            exit 1
        }
        
        $result = New-DraftEmail -Outlook $outlook -DraftData $draftData
    }
    
    # Output result
    if ($result.success) {
        Write-Host "Draft saved successfully!" -ForegroundColor Green
        $result | ConvertTo-Json -Depth 2
    } else {
        Write-Error $result.error
        exit 1
    }
    
} catch {
    Write-Error "Error processing draft: $($_.Exception.Message)"
    Write-Host "JSON Input was: $jsonInput"
    exit 1
}