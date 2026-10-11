      ******************************************************************
      * FEESCHED  -  OUTBOUND WIRE / SWIFT FEE SCHEDULE (COPYBOOK)     *
      *----------------------------------------------------------------*
      * Owner    : Meridian Global Bank - Payments Systems             *
      * Used by  : FEECALC01 (nightly fee calculation batch)           *
      * Version  : 2026.03.01                                          *
      *                                                                *
      * This copybook is the single place the fee schedule lives.     *
      * FEECALC01 never hard-codes a tariff value; it reads the band  *
      * table, the segment multipliers, the cap and the SWIFT rail    *
      * surcharge from here.                                          *
      *                                                                *
      * BAND TABLE (upper bound is INCLUSIVE; bands are tested in     *
      * ascending order, first match wins):                           *
      *   1 : amount <=        10,000.00  base 15.00  rate 0.000000   *
      *   2 : amount <=       100,000.00  base 25.00  rate 0.000100   *
      *   3 : amount <=     1,000,000.00  base 35.00  rate 0.000050   *
      *   4 : amount >      1,000,000.00  base 50.00  rate 0.000025   *
      *       (band 4 upper bound is the field maximum = sentinel)    *
      *                                                                *
      * The rate is a scaled decimal (PIC V9(6)); 1.0 bps = 0.000100. *
      * Multiplying a PIC 9(13)V99 amount by a PIC V9(6) rate yields  *
      * an exact 8-decimal intermediate, so the only rounding in the  *
      * program is the explicit ROUNDED on the COMPUTE statements.    *
      ******************************************************************
       01  FEESCHED-VERSION                PIC X(10) VALUE '2026.03.01'.
       01  FEESCHED-BAND-COUNT             PIC 9     VALUE 4.

      *    Band data laid out as FILLER groups with VALUE clauses ...
       01  FEESCHED-BAND-DATA.
           05  FILLER.
               10  FILLER                  PIC 9(13)V99
                                           VALUE 10000.00.
               10  FILLER                  PIC 9(5)V99
                                           VALUE 15.00.
               10  FILLER                  PIC V9(6)
                                           VALUE 0.000000.
           05  FILLER.
               10  FILLER                  PIC 9(13)V99
                                           VALUE 100000.00.
               10  FILLER                  PIC 9(5)V99
                                           VALUE 25.00.
               10  FILLER                  PIC V9(6)
                                           VALUE 0.000100.
           05  FILLER.
               10  FILLER                  PIC 9(13)V99
                                           VALUE 1000000.00.
               10  FILLER                  PIC 9(5)V99
                                           VALUE 35.00.
               10  FILLER                  PIC V9(6)
                                           VALUE 0.000050.
           05  FILLER.
               10  FILLER                  PIC 9(13)V99
                                           VALUE 9999999999999.99.
               10  FILLER                  PIC 9(5)V99
                                           VALUE 50.00.
               10  FILLER                  PIC V9(6)
                                           VALUE 0.000025.

      *    ... and redefined as an indexed table for the band search.
       01  FEESCHED-BAND-TABLE REDEFINES FEESCHED-BAND-DATA.
           05  FS-BAND OCCURS 4 TIMES INDEXED BY FS-IDX.
               10  FS-BAND-UPPER           PIC 9(13)V99.
               10  FS-BAND-BASE-FEE        PIC 9(5)V99.
               10  FS-BAND-BPS-RATE        PIC V9(6).

      *    Customer segment multipliers applied to the capped band fee.
       01  FEESCHED-SEGMENT-RATES.
           05  FS-MULT-INSTITUTIONAL       PIC 9V99  VALUE 0.80.
           05  FS-MULT-CORPORATE           PIC 9V99  VALUE 1.00.
           05  FS-MULT-RETAIL              PIC 9V99  VALUE 1.10.

      *    Cap applies to the banded fee only (before multiplier and
      *    before the rail surcharge).  The SWIFT surcharge is added
      *    last and is never capped.
       01  FEESCHED-LIMITS.
           05  FS-FEE-CAP                  PIC 9(5)V99 VALUE 250.00.
           05  FS-SWIFT-SURCHARGE          PIC 9(3)V99 VALUE 12.00.

      *    Input code values.  'WIRE_' is accepted as an alias of
      *    'WIRE ' because some upstream extracts pad with underscore.
       01  FEESCHED-CODES.
           05  FS-SEG-INSTITUTIONAL        PIC X     VALUE 'I'.
           05  FS-SEG-CORPORATE            PIC X     VALUE 'C'.
           05  FS-SEG-RETAIL               PIC X     VALUE 'R'.
           05  FS-RAIL-WIRE                PIC X(5)  VALUE 'WIRE '.
           05  FS-RAIL-WIRE-ALT            PIC X(5)  VALUE 'WIRE_'.
           05  FS-RAIL-SWIFT               PIC X(5)  VALUE 'SWIFT'.
