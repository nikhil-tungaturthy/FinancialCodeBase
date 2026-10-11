Attribute VB_Name = "modExceptionRouting"
'=====================================================================
' Module    : modExceptionRouting
' Project   : PRD32 - Payments Review Desk (Visual Basic 6.0 SP6)
' Purpose   : Route a held payment exception to a review queue, grade
'             its severity (1-4) and decide whether supervisor sign-off
'             is required before any release action is permitted.
'
' Called by : frmReviewQueue        (manual route / re-route by analyst)
'             clsHoldImporter       (overnight HOLDXTRT file import)
'
' Reason codes are the "Rnn" codes written by the mainframe hold
' extract (HOLDXTRT).  Queue codes must match PRD_QUEUE.QUEUE_CODE in
' the desk database exactly - they are used as keys, not labels.
'
' Rules (in evaluation order)
'   1. R07 screening hit  -> FCR-SCREEN, severity 4, supervisor always
'   2. segment I and amount >= 250,000 -> INST-HV
'   3. segment R                        -> RETAIL-STD
'   4. anything else                    -> CORP-STD
'   Supervisor required when severity >= 3 or amount >= 100,000.
'
' History
'   1999-04-12  J. Dalgaard   Initial version (R01-R06, R08, R09)
'   2001-11-05  K. Whitfield  Added R10 PURPOSE and R11 CCY/RAIL
'   2003-09-02  K. Whitfield  Added FCR-SCREEN queue for R07 screening
'                             hits; screening always escalates
'   2008-01-15  M. Osei       Raised institutional HV threshold from
'                             100,000 to 250,000 (PRD-CR-0412)
'   2011-06-30  M. Osei       Supervisor rule extended: sev >= 3 OR
'                             amount >= 100,000 (was sev >= 3 only)
'=====================================================================
Option Explicit

' ---- Queue codes (PRD_QUEUE.QUEUE_CODE) -----------------------------
Public Const QUEUE_RETAIL_STD As String = "RETAIL-STD"
Public Const QUEUE_CORP_STD As String = "CORP-STD"
Public Const QUEUE_INST_HV As String = "INST-HV"
Public Const QUEUE_FCR_SCREEN As String = "FCR-SCREEN"

' ---- Severity grades ------------------------------------------------
Public Const SEV_LOW As Integer = 1
Public Const SEV_MEDIUM As Integer = 2
Public Const SEV_HIGH As Integer = 3
Public Const SEV_CRITICAL As Integer = 4

' ---- Thresholds (USD, Currency = 4 implied decimals) ----------------
Public Const HV_AMOUNT_THRESHOLD As Currency = 250000@
Public Const SUPERVISOR_AMOUNT_THRESHOLD As Currency = 100000@
Public Const SUPERVISOR_SEVERITY_THRESHOLD As Integer = 3

' ---- Segment codes (CUSTMAST.SEG_CD) --------------------------------
Public Const SEG_INSTITUTIONAL As String = "I"
Public Const SEG_CORPORATE As String = "C"
Public Const SEG_RETAIL As String = "R"

' ---- Reason codes (HOLDXTRT) ----------------------------------------
Public Const REASON_INVALID_ACCT As String = "R01"
Public Const REASON_MISSING_BIC As String = "R02"
Public Const REASON_NAME_MISMATCH As String = "R03"
Public Const REASON_DUPLICATE As String = "R04"
Public Const REASON_LIMIT As String = "R05"
Public Const REASON_CUTOFF As String = "R06"
Public Const REASON_SCREENING As String = "R07"
Public Const REASON_NSF As String = "R08"
Public Const REASON_STALE_DATE As String = "R09"
Public Const REASON_PURPOSE As String = "R10"
Public Const REASON_CCY_RAIL As String = "R11"

Public Type RoutingResult
    Queue As String
    Severity As Integer
    RequiresSupervisor As Boolean
    ReasonCode As String
    ReasonText As String
End Type

'---------------------------------------------------------------------
' RouteException
'   reasonCode : HOLDXTRT reason code, e.g. "R03"
'   amountUsd  : payment value converted to USD by the extract
'   segment    : CUSTMAST segment code I / C / R
' Returns a populated RoutingResult.  Never raises: unknown reason
' codes are graded SEV_MEDIUM and unknown segments go to CORP-STD.
'---------------------------------------------------------------------
Public Function RouteException(ByVal reasonCode As String, _
                               ByVal amountUsd As Currency, _
                               ByVal segment As String) As RoutingResult
    Dim result As RoutingResult
    Dim code As String
    Dim seg As String

    code = UCase$(Trim$(reasonCode))
    seg = UCase$(Trim$(segment))

    result.ReasonCode = code
    result.ReasonText = ReasonText(code)
    result.Severity = SeverityForReason(code)

    If code = REASON_SCREENING Then
        ' Screening hits always go to Financial Crime Risk, whatever
        ' the amount or segment, and always need a supervisor.
        result.Queue = QUEUE_FCR_SCREEN
        result.Severity = SEV_CRITICAL
        result.RequiresSupervisor = True
    Else
        Select Case True
            Case seg = SEG_INSTITUTIONAL And amountUsd >= HV_AMOUNT_THRESHOLD
                result.Queue = QUEUE_INST_HV
            Case seg = SEG_RETAIL
                result.Queue = QUEUE_RETAIL_STD
            Case Else
                ' Corporate, institutional below the HV threshold, and
                ' any segment code the desk does not recognise.
                result.Queue = QUEUE_CORP_STD
        End Select

        result.RequiresSupervisor = _
            (result.Severity >= SUPERVISOR_SEVERITY_THRESHOLD) Or _
            (amountUsd >= SUPERVISOR_AMOUNT_THRESHOLD)
    End If

    RouteException = result
End Function

'---------------------------------------------------------------------
' SeverityForReason - severity grade per reason code.
' Keep in step with the PRD_REASON table; this copy exists so the
' desk still routes when the database is unavailable.
'---------------------------------------------------------------------
Private Function SeverityForReason(ByVal code As String) As Integer
    Select Case code
        Case REASON_INVALID_ACCT:  SeverityForReason = SEV_HIGH
        Case REASON_MISSING_BIC:   SeverityForReason = SEV_MEDIUM
        Case REASON_NAME_MISMATCH: SeverityForReason = SEV_HIGH
        Case REASON_DUPLICATE:     SeverityForReason = SEV_HIGH
        Case REASON_LIMIT:         SeverityForReason = SEV_HIGH
        Case REASON_CUTOFF:        SeverityForReason = SEV_MEDIUM
        Case REASON_SCREENING:     SeverityForReason = SEV_CRITICAL
        Case REASON_NSF:           SeverityForReason = SEV_MEDIUM
        Case REASON_STALE_DATE:    SeverityForReason = SEV_LOW
        Case REASON_PURPOSE:       SeverityForReason = SEV_MEDIUM
        Case REASON_CCY_RAIL:      SeverityForReason = SEV_HIGH
        Case Else:                 SeverityForReason = SEV_MEDIUM
    End Select
End Function

'---------------------------------------------------------------------
' ReasonText - short description shown in the queue grid.
'---------------------------------------------------------------------
Public Function ReasonText(ByVal code As String) As String
    Select Case UCase$(Trim$(code))
        Case REASON_INVALID_ACCT:  ReasonText = "INVALID ACCT"
        Case REASON_MISSING_BIC:   ReasonText = "MISSING BIC"
        Case REASON_NAME_MISMATCH: ReasonText = "NAME MISMATCH"
        Case REASON_DUPLICATE:     ReasonText = "DUPLICATE"
        Case REASON_LIMIT:         ReasonText = "LIMIT"
        Case REASON_CUTOFF:        ReasonText = "CUTOFF"
        Case REASON_SCREENING:     ReasonText = "SCREENING"
        Case REASON_NSF:           ReasonText = "NSF"
        Case REASON_STALE_DATE:    ReasonText = "STALE DATE"
        Case REASON_PURPOSE:       ReasonText = "PURPOSE"
        Case REASON_CCY_RAIL:      ReasonText = "CCY/RAIL"
        Case Else:                 ReasonText = "UNKNOWN (" & code & ")"
    End Select
End Function

'---------------------------------------------------------------------
' SeverityText - grade label for display.
'---------------------------------------------------------------------
Public Function SeverityText(ByVal sev As Integer) As String
    Select Case sev
        Case SEV_LOW:      SeverityText = "LOW"
        Case SEV_MEDIUM:   SeverityText = "MEDIUM"
        Case SEV_HIGH:     SeverityText = "HIGH"
        Case SEV_CRITICAL: SeverityText = "CRITICAL"
        Case Else:         SeverityText = "SEV " & CStr(sev)
    End Select
End Function

'---------------------------------------------------------------------
' IsKnownReason - True when the code has an entry in the table above.
'---------------------------------------------------------------------
Public Function IsKnownReason(ByVal code As String) As Boolean
    Select Case UCase$(Trim$(code))
        Case REASON_INVALID_ACCT, REASON_MISSING_BIC, REASON_NAME_MISMATCH, _
             REASON_DUPLICATE, REASON_LIMIT, REASON_CUTOFF, REASON_SCREENING, _
             REASON_NSF, REASON_STALE_DATE, REASON_PURPOSE, REASON_CCY_RAIL
            IsKnownReason = True
        Case Else
            IsKnownReason = False
    End Select
End Function
