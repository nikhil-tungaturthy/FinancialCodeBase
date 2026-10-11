VERSION 5.00
Begin VB.Form frmReviewQueue 
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "Payments Review Desk - Route Exception"
   ClientHeight    =   3615
   ClientLeft      =   45
   ClientTop       =   375
   ClientWidth     =   6225
   BeginProperty Font 
      Name            =   "Tahoma"
      Size            =   8.25
      Charset         =   0
      Weight          =   400
      Underline       =   0   'False
      Italic          =   0   'False
      Strikethrough   =   0   'False
   EndProperty
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   3615
   ScaleWidth      =   6225
   ShowInTaskbar   =   0   'False
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdClose 
      Cancel          =   -1  'True
      Caption         =   "&Close"
      Height          =   375
      Left            =   4800
      TabIndex        =   7
      Top             =   3060
      Width           =   1215
   End
   Begin VB.CommandButton cmdRoute 
      Caption         =   "&Route"
      Default         =   -1  'True
      Height          =   375
      Left            =   3480
      TabIndex        =   6
      Top             =   3060
      Width           =   1215
   End
   Begin VB.ComboBox cboSegment 
      Height          =   315
      Left            =   1560
      Style           =   2  'Dropdown List
      TabIndex        =   5
      Top             =   1140
      Width           =   2175
   End
   Begin VB.TextBox txtAmount 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1560
      TabIndex        =   3
      Text            =   "0.00"
      Top             =   690
      Width           =   2175
   End
   Begin VB.ComboBox cboReason 
      Height          =   315
      Left            =   1560
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   240
      Width           =   4455
   End
   Begin VB.Frame fraResult 
      Caption         =   " Routing "
      Height          =   1335
      Left            =   180
      TabIndex        =   8
      Top             =   1620
      Width           =   5835
      Begin VB.Label lblQueueValue 
         Caption         =   "-"
         BeginProperty Font 
            Name            =   "Tahoma"
            Size            =   8.25
            Charset         =   0
            Weight          =   700
            Underline       =   0   'False
            Italic          =   0   'False
            Strikethrough   =   0   'False
         EndProperty
         Height          =   255
         Left            =   1380
         TabIndex        =   14
         Top             =   330
         Width           =   2535
      End
      Begin VB.Label lblSeverityValue 
         Caption         =   "-"
         Height          =   255
         Left            =   1380
         TabIndex        =   13
         Top             =   630
         Width           =   2535
      End
      Begin VB.Label lblSupervisorValue 
         Caption         =   "-"
         Height          =   255
         Left            =   1380
         TabIndex        =   12
         Top             =   930
         Width           =   4215
      End
      Begin VB.Label lblQueue 
         Caption         =   "Queue:"
         Height          =   255
         Left            =   240
         TabIndex        =   11
         Top             =   330
         Width           =   1095
      End
      Begin VB.Label lblSeverity 
         Caption         =   "Severity:"
         Height          =   255
         Left            =   240
         TabIndex        =   10
         Top             =   630
         Width           =   1095
      End
      Begin VB.Label lblSupervisor 
         Caption         =   "Supervisor:"
         Height          =   255
         Left            =   240
         TabIndex        =   9
         Top             =   930
         Width           =   1095
      End
   End
   Begin VB.Label lblSegment 
      Caption         =   "Segment:"
      Height          =   255
      Left            =   180
      TabIndex        =   4
      Top             =   1170
      Width           =   1215
   End
   Begin VB.Label lblAmount 
      Caption         =   "Amount (USD):"
      Height          =   255
      Left            =   180
      TabIndex        =   2
      Top             =   720
      Width           =   1335
   End
   Begin VB.Label lblReason 
      Caption         =   "Reason code:"
      Height          =   255
      Left            =   180
      TabIndex        =   0
      Top             =   270
      Width           =   1335
   End
End
Attribute VB_Name = "frmReviewQueue"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
'=====================================================================
' Form      : frmReviewQueue
' Project   : PRD32 - Payments Review Desk
' Purpose   : Analyst dialog to route (or re-route) a held payment.
'             Thin UI over modExceptionRouting.RouteException; all
'             routing rules live in the module, none in this form.
'=====================================================================
Option Explicit

Private m_ReasonCodes(1 To 11) As String

Private Sub Form_Load()
    Dim i As Integer

    m_ReasonCodes(1) = REASON_INVALID_ACCT
    m_ReasonCodes(2) = REASON_MISSING_BIC
    m_ReasonCodes(3) = REASON_NAME_MISMATCH
    m_ReasonCodes(4) = REASON_DUPLICATE
    m_ReasonCodes(5) = REASON_LIMIT
    m_ReasonCodes(6) = REASON_CUTOFF
    m_ReasonCodes(7) = REASON_SCREENING
    m_ReasonCodes(8) = REASON_NSF
    m_ReasonCodes(9) = REASON_STALE_DATE
    m_ReasonCodes(10) = REASON_PURPOSE
    m_ReasonCodes(11) = REASON_CCY_RAIL

    cboReason.Clear
    For i = LBound(m_ReasonCodes) To UBound(m_ReasonCodes)
        cboReason.AddItem m_ReasonCodes(i) & " - " & ReasonText(m_ReasonCodes(i))
    Next i
    cboReason.ListIndex = 0

    cboSegment.Clear
    cboSegment.AddItem SEG_INSTITUTIONAL & " - Institutional"
    cboSegment.AddItem SEG_CORPORATE & " - Corporate"
    cboSegment.AddItem SEG_RETAIL & " - Retail"
    cboSegment.ListIndex = 1

    ClearResult
End Sub

Private Sub cmdRoute_Click()
    Dim amount As Currency
    Dim result As RoutingResult

    On Error GoTo BadAmount
    amount = CCur(Trim$(txtAmount.Text))
    On Error GoTo 0

    If amount < 0 Then
        MsgBox "Amount must not be negative.", vbExclamation, Me.Caption
        txtAmount.SetFocus
        Exit Sub
    End If

    result = RouteException(SelectedReasonCode(), amount, SelectedSegmentCode())

    lblQueueValue.Caption = result.Queue
    lblSeverityValue.Caption = CStr(result.Severity) & " - " & SeverityText(result.Severity)
    If result.RequiresSupervisor Then
        lblSupervisorValue.Caption = "REQUIRED before release"
        lblSupervisorValue.ForeColor = vbRed
    Else
        lblSupervisorValue.Caption = "Not required"
        lblSupervisorValue.ForeColor = vbWindowText
    End If
    Exit Sub

BadAmount:
    MsgBox "Enter the USD amount as a number, e.g. 480000.00", vbExclamation, Me.Caption
    txtAmount.SelStart = 0
    txtAmount.SelLength = Len(txtAmount.Text)
    txtAmount.SetFocus
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub

Private Sub cboReason_Click()
    ClearResult
End Sub

Private Sub cboSegment_Click()
    ClearResult
End Sub

Private Sub txtAmount_Change()
    ClearResult
End Sub

Private Function SelectedReasonCode() As String
    If cboReason.ListIndex < 0 Then
        SelectedReasonCode = ""
    Else
        SelectedReasonCode = m_ReasonCodes(cboReason.ListIndex + 1)
    End If
End Function

Private Function SelectedSegmentCode() As String
    ' List entries are "<code> - <label>"; the code is the first character.
    If cboSegment.ListIndex < 0 Then
        SelectedSegmentCode = ""
    Else
        SelectedSegmentCode = Left$(cboSegment.List(cboSegment.ListIndex), 1)
    End If
End Function

Private Sub ClearResult()
    lblQueueValue.Caption = "-"
    lblSeverityValue.Caption = "-"
    lblSupervisorValue.Caption = "-"
    lblSupervisorValue.ForeColor = vbWindowText
End Sub
