       IDENTIFICATION DIVISION.
       PROGRAM-ID. FEECALC01.
       AUTHOR. MERIDIAN GLOBAL BANK - PAYMENTS SYSTEMS.
      ******************************************************************
      * FEECALC01  -  OUTBOUND WIRE / SWIFT FEE CALCULATION (BATCH)    *
      *----------------------------------------------------------------*
      * Reads the FEEIN extract (one payment per record), computes the *
      * customer fee from the tariff in copybook FEESCHED, and writes  *
      * FEEOUT with the input echoed and the fee appended.             *
      *                                                                *
      * FEEIN  record (LINE SEQUENTIAL, 21 bytes)                      *
      *   01-15  AMOUNT        PIC 9(13)V99  unsigned, implied 2 dp    *
      *   16     SEGMENT-CODE  PIC X         I / C / R                 *
      *   17-21  RAIL-CODE     PIC X(5)      'WIRE ' or 'SWIFT'        *
      *                                                                *
      * FEEOUT record (LINE SEQUENTIAL, 34 bytes)                      *
      *   01-21  input record echoed unchanged                         *
      *   22-30  FEE           PIC 9(7)V99   implied 2 dp              *
      *   31     BAND          PIC 9         1-4 (0 when rejected)     *
      *   32     CAP-FLAG      PIC X         Y when cap applied        *
      *   33-34  STATUS        PIC XX        00 ok                     *
      *                                      01 bad segment code       *
      *                                      02 bad rail code          *
      *                                      03 amount not numeric     *
      *                                                                *
      * CALCULATION (see FEESCHED for the values)                      *
      *   2100  band      = first band whose upper bound >= amount     *
      *   2200  banded    = base(band) + ROUNDED(amount * rate(band))  *
      *   2300  capped    = MIN(banded, FEE-CAP)                       *
      *   2400  segmented = ROUNDED(capped * multiplier(segment))      *
      *   2500  fee       = segmented + surcharge(rail)                *
      *   ROUNDED uses the compiler default mode, which for GnuCOBOL   *
      *   is NEAREST-AWAY-FROM-ZERO (= round half up for positives).   *
      *                                                                *
      * RETURN-CODE: 0 all records priced, 4 one or more records       *
      * rejected (written with a non-zero STATUS), 12 file error.      *
      *                                                                *
      * Files are assigned by external name; set DD_FEEIN / DD_FEEOUT  *
      * (or FEEIN / FEEOUT) in the environment before running.         *
      ******************************************************************
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT FEEIN  ASSIGN TO "FEEIN"
                         ORGANIZATION IS LINE SEQUENTIAL
                         FILE STATUS IS WS-FEEIN-STATUS.
           SELECT FEEOUT ASSIGN TO "FEEOUT"
                         ORGANIZATION IS LINE SEQUENTIAL
                         FILE STATUS IS WS-FEEOUT-STATUS.

       DATA DIVISION.
       FILE SECTION.
       FD  FEEIN.
       01  FEEIN-RECORD                    PIC X(21).
       FD  FEEOUT.
       01  FEEOUT-RECORD                   PIC X(34).

       WORKING-STORAGE SECTION.
       01  WS-FEEIN-STATUS                 PIC XX    VALUE SPACES.
       01  WS-FEEOUT-STATUS                PIC XX    VALUE SPACES.

       01  WS-EOF-FLAG                     PIC X     VALUE 'N'.
           88  WS-EOF                                VALUE 'Y'.

       01  WS-COUNTERS.
           05  WS-READ-COUNT               PIC 9(7)  VALUE ZERO.
           05  WS-WRITTEN-COUNT            PIC 9(7)  VALUE ZERO.
           05  WS-ERROR-COUNT              PIC 9(7)  VALUE ZERO.
           05  WS-SKIPPED-COUNT            PIC 9(7)  VALUE ZERO.

      *    Input record image (READ ... INTO).
       01  WS-INPUT-RECORD.
           05  WS-IN-AMOUNT                PIC 9(13)V99.
           05  WS-IN-SEGMENT               PIC X.
           05  WS-IN-RAIL                  PIC X(5).

      *    Output record image (WRITE ... FROM).
       01  WS-OUTPUT-RECORD.
           05  WS-OUT-ECHO                 PIC X(21).
           05  WS-OUT-FEE                  PIC 9(7)V99.
           05  WS-OUT-BAND                 PIC 9.
           05  WS-OUT-CAPPED               PIC X.
           05  WS-OUT-STATUS               PIC XX.

      *    Work fields.  The pre-cap fields are deliberately wider
      *    than the output fee: the maximum amount in band 4 gives a
      *    nine-digit bps component (250,000,000.00) before the cap.
       01  WS-WORK-AREAS.
           05  WS-BAND                     PIC 9.
           05  WS-BAND-FOUND-FLAG          PIC X.
               88  WS-BAND-FOUND                     VALUE 'Y'.
           05  WS-BPS-AMOUNT               PIC 9(10)V99.
           05  WS-BANDED-FEE               PIC 9(10)V99.
           05  WS-CAPPED-FEE               PIC 9(5)V99.
           05  WS-MULTIPLIER               PIC 9V99.
           05  WS-SEGMENT-FEE              PIC 9(7)V99.
           05  WS-SURCHARGE                PIC 9(3)V99.
           05  WS-FINAL-FEE                PIC 9(7)V99.
           05  WS-RECORD-STATUS            PIC XX.
               88  WS-RECORD-OK                      VALUE '00'.
               88  WS-BAD-SEGMENT                    VALUE '01'.
               88  WS-BAD-RAIL                       VALUE '02'.
               88  WS-BAD-AMOUNT                     VALUE '03'.

      *    Tariff: bands, multipliers, cap, surcharge, code values.
       COPY FEESCHED.

       PROCEDURE DIVISION.
      ******************************************************************
       0000-MAIN.
      ******************************************************************
           PERFORM 1000-INITIALIZE
           PERFORM 2000-PROCESS-RECORD UNTIL WS-EOF
           PERFORM 3000-TERMINATE
           STOP RUN.

      ******************************************************************
       1000-INITIALIZE.
      *    Open both files, abort with RC 12 on any file error, then
      *    prime the read loop with the first record.
      ******************************************************************
           DISPLAY 'FEECALC01: START, FEE SCHEDULE ' FEESCHED-VERSION
           OPEN INPUT FEEIN
           IF WS-FEEIN-STATUS NOT = '00'
               DISPLAY 'FEECALC01: OPEN FEEIN FAILED, STATUS '
                       WS-FEEIN-STATUS
               MOVE 12 TO RETURN-CODE
               STOP RUN
           END-IF
           OPEN OUTPUT FEEOUT
           IF WS-FEEOUT-STATUS NOT = '00'
               DISPLAY 'FEECALC01: OPEN FEEOUT FAILED, STATUS '
                       WS-FEEOUT-STATUS
               MOVE 12 TO RETURN-CODE
               STOP RUN
           END-IF
           PERFORM 1100-READ-FEEIN.

      ******************************************************************
       1100-READ-FEEIN.
      ******************************************************************
           READ FEEIN INTO WS-INPUT-RECORD
               AT END
                   SET WS-EOF TO TRUE
               NOT AT END
                   ADD 1 TO WS-READ-COUNT
           END-READ.

      ******************************************************************
       2000-PROCESS-RECORD.
      *    One pass per input record.  Blank records are skipped
      *    silently; everything else produces exactly one FEEOUT line.
      ******************************************************************
           IF WS-INPUT-RECORD = SPACES
               ADD 1 TO WS-SKIPPED-COUNT
           ELSE
               PERFORM 2050-VALIDATE-INPUT
               IF WS-RECORD-OK
                   PERFORM 2100-SELECT-BAND
                   PERFORM 2200-COMPUTE-BANDED-FEE
                   PERFORM 2300-APPLY-CAP
                   PERFORM 2400-APPLY-SEGMENT
                   PERFORM 2500-APPLY-RAIL-SURCHARGE
               ELSE
                   ADD 1 TO WS-ERROR-COUNT
               END-IF
               PERFORM 2900-WRITE-FEEOUT
           END-IF
           PERFORM 1100-READ-FEEIN.

      ******************************************************************
       2050-VALIDATE-INPUT.
      *    Reset the work fields and classify the record.  Checks run
      *    in the order amount (03), segment (01), rail (02); the
      *    first failure is the one reported.
      ******************************************************************
           SET WS-RECORD-OK TO TRUE
           MOVE ZERO TO WS-BAND
                        WS-BPS-AMOUNT
                        WS-BANDED-FEE
                        WS-CAPPED-FEE
                        WS-MULTIPLIER
                        WS-SEGMENT-FEE
                        WS-SURCHARGE
                        WS-FINAL-FEE
           MOVE 'N' TO WS-OUT-CAPPED

           IF WS-IN-AMOUNT IS NOT NUMERIC
               SET WS-BAD-AMOUNT TO TRUE
           END-IF

           IF WS-RECORD-OK
               EVALUATE WS-IN-SEGMENT
                   WHEN FS-SEG-INSTITUTIONAL
                       MOVE FS-MULT-INSTITUTIONAL TO WS-MULTIPLIER
                   WHEN FS-SEG-CORPORATE
                       MOVE FS-MULT-CORPORATE     TO WS-MULTIPLIER
                   WHEN FS-SEG-RETAIL
                       MOVE FS-MULT-RETAIL        TO WS-MULTIPLIER
                   WHEN OTHER
                       SET WS-BAD-SEGMENT TO TRUE
               END-EVALUATE
           END-IF

           IF WS-RECORD-OK
               EVALUATE WS-IN-RAIL
                   WHEN FS-RAIL-WIRE
                       MOVE ZERO               TO WS-SURCHARGE
                   WHEN FS-RAIL-WIRE-ALT
                       MOVE ZERO               TO WS-SURCHARGE
                   WHEN FS-RAIL-SWIFT
                       MOVE FS-SWIFT-SURCHARGE TO WS-SURCHARGE
                   WHEN OTHER
                       SET WS-BAD-RAIL TO TRUE
               END-EVALUATE
           END-IF.

      ******************************************************************
       2100-SELECT-BAND.
      *    Walk the band table in ascending order; the first band whose
      *    inclusive upper bound is >= the amount is the one priced.
      *    Band 4 carries the field maximum as its bound, so the search
      *    always terminates with a band.
      ******************************************************************
           MOVE 'N' TO WS-BAND-FOUND-FLAG
           PERFORM VARYING FS-IDX FROM 1 BY 1
                   UNTIL WS-BAND-FOUND
                      OR FS-IDX > FEESCHED-BAND-COUNT
               IF WS-IN-AMOUNT <= FS-BAND-UPPER(FS-IDX)
                   SET WS-BAND-FOUND TO TRUE
                   SET WS-BAND TO FS-IDX
               END-IF
           END-PERFORM.

      ******************************************************************
       2200-COMPUTE-BANDED-FEE.
      *    bps component = amount * rate, rounded half up to 2 dp
      *    banded fee    = base + bps component (no further rounding,
      *                    both operands already carry 2 dp)
      ******************************************************************
           COMPUTE WS-BPS-AMOUNT ROUNDED
               = WS-IN-AMOUNT * FS-BAND-BPS-RATE(WS-BAND)
           COMPUTE WS-BANDED-FEE
               = FS-BAND-BASE-FEE(WS-BAND) + WS-BPS-AMOUNT.

      ******************************************************************
       2300-APPLY-CAP.
      *    The cap applies to the banded fee only.  A banded fee equal
      *    to the cap is NOT a cap hit (strict greater-than test).
      ******************************************************************
           IF WS-BANDED-FEE > FS-FEE-CAP
               MOVE FS-FEE-CAP TO WS-CAPPED-FEE
               MOVE 'Y'        TO WS-OUT-CAPPED
           ELSE
               MOVE WS-BANDED-FEE TO WS-CAPPED-FEE
               MOVE 'N'           TO WS-OUT-CAPPED
           END-IF.

      ******************************************************************
       2400-APPLY-SEGMENT.
      *    Segment multiplier on the capped fee, rounded half up.
      ******************************************************************
           COMPUTE WS-SEGMENT-FEE ROUNDED
               = WS-CAPPED-FEE * WS-MULTIPLIER.

      ******************************************************************
       2500-APPLY-RAIL-SURCHARGE.
      *    Rail surcharge is added after the multiplier and is never
      *    subject to the cap.
      ******************************************************************
           COMPUTE WS-FINAL-FEE
               = WS-SEGMENT-FEE + WS-SURCHARGE.

      ******************************************************************
       2900-WRITE-FEEOUT.
      ******************************************************************
           MOVE WS-INPUT-RECORD  TO WS-OUT-ECHO
           MOVE WS-FINAL-FEE     TO WS-OUT-FEE
           MOVE WS-BAND          TO WS-OUT-BAND
           MOVE WS-RECORD-STATUS TO WS-OUT-STATUS
           WRITE FEEOUT-RECORD FROM WS-OUTPUT-RECORD
           IF WS-FEEOUT-STATUS NOT = '00'
               DISPLAY 'FEECALC01: WRITE FEEOUT FAILED, STATUS '
                       WS-FEEOUT-STATUS
               MOVE 12 TO RETURN-CODE
               STOP RUN
           END-IF
           ADD 1 TO WS-WRITTEN-COUNT.

      ******************************************************************
       3000-TERMINATE.
      ******************************************************************
           CLOSE FEEIN
                 FEEOUT
           DISPLAY 'FEECALC01: END, READ='    WS-READ-COUNT
                   ' WRITTEN=' WS-WRITTEN-COUNT
                   ' ERRORS='  WS-ERROR-COUNT
                   ' SKIPPED=' WS-SKIPPED-COUNT
           IF WS-ERROR-COUNT > ZERO
               MOVE 4 TO RETURN-CODE
           END-IF.
