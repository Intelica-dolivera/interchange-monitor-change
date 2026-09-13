f 1:
Reserved → definido — TC 04 - TCR 9 (1)
Posición `151-168` (Reserved) se partió
Antes: `151-168` Reserved
Ahora: `151-153` VFC Reclassification Reason. Reserved restante: 154-168 Reserved
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 2:
Reserved → definido — TC 05 - TCR 2 Colombia (1)
Posición `5-16`
Antes: Reserved
Ahora: Tip Amount
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 3:
Reserved → definido — TC 33 - TCR 1 BASE II Clearing and Settlement Advice (1)
Posición `161-168`
Antes: Reserved
Ahora: Payment Facilitator ID
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 4:
Reserved → definido — TC 33.A - CP 04 TCR 0 Level II Data (1)
Posición `99-168` (Reserved) se partió
Antes: `99-168` Reserved
Ahora: `99` Merchant CEDP Verified Indicator. Reserved restante: 100-168 Reserved
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 5:
Reserved → definido — TC 33.A - CP 09 TCR 4 - Recipient Name (Split) (1)
Posición `110-168` (Reserved) se partió
Antes: `110-168` Reserved
Ahora: `110-117` Payee Date of Birth. Reserved restante: 118-137 Reserved, 138-139 Reserved, 140-168 Reserved
Razón: Confirmado en grilla y ficha.
Obs: No ha contemplado todos los campos que dejaron de ser reservados como comenté antes. Antes era:
110-168 59 AN Reserved
Ahora es:
110-117 8 AN Payee Date of Birth
118-137 20 ANS Payee Phone Number
138-139 2 AN Recipient State
140-168 29 AN Reserved

Caso 6:
Reserved → definido — TC 33.A - CP 12 TCR 1 Merchant Data (1)
Posición `149-168` (Reserved) se partió
Antes: `149-168` Reserved
Ahora: `149-160` Foreign Retailer Transaction Amount. Reserved restante: 161-168 Reserved
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 7:
Reserved → definido — TC 33.A - CP 12 TCR 5 Transaction Data (1)
Posición `148-168` (Reserved) se partió
Antes: `148-168` Reserved
Ahora: `148-157` Mastercard - Service Location Postal Code. Reserved restante: 158-168 Reserved
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 8:
Definido → Reserved — TC 33.A - CP 12 TCR 2 Merchant Data (1)
Posición `5-34`
Antes: Mastercard - Account Level Management Service Data
Ahora: Reserved
Razón: Confirmado en grilla y ficha.
Obs: Todo Ok

Caso 9:
TC 05 - TCR 0 (11)
`133-136` — Merchant Category Code · Ficha (description)
Antes: Indicates merchant’s type of business product or service. The field must contain a valid four-digit numeric Merchant Category Code (MCC). For Reimbursement Attribute 1, 2, G, or H, the entry must be 6011. National—U.S.: MCCs 5962, 5966, and 5967 cannot be submitted with l Reimbursement Attribute A, D or J. MCCs 5962 or 5964 – 5969 cannot be submitted with a Requested l Payment Service (RPS) of A, an Authorization Characteristic Indicator (ACI) of A or E, and a POS Entry Mode of 01 or 10. Only MCC 5411 is valid on Supermarket transactions (Reimbursement l Attribute 4). VIC Edits: MCC 6010 and 6011 are invalid for original sales drafts and credit l vouchers and their reversals. For custom payment service original purchase transactions and their l reversals and Electronic Data Quality Program transactions, this field must have the same contents as in the Authorization Request (V.I.P. Field 18 converted to unpacked numeric). If multiple authorizations and/or an authorization reversal were submitted, this field must contain the Merchant Category Code from the first authorization response. For the CPS/Automated Fuel Dispenser custom payment service, the l MCC must be 5542. For the CPS/ATM custom payment service, the MCC must be 6011. l VIC Edit, National—Brazil: To qualify for the CPS/Retail-Petrol PSIRF, the MCC must be 5541. l To qualify for the CPS/Restaurant PSIRF, the MCC must be 5812 or l 5814. VIC Edit, National—U.S.: Only MCCs 7523, and 7832 are valid on EPS transactions (Reimbursement Attribute 3). VIC Edit, National—Malaysia and Macau: Only MCCs 5814, 4784 and 7832 are valid on EPS transactions (Reimbursement Attribute 3). VIC Edit, National—Hong Kong*, Australia, New Zealand, Thailand, India and Indonesia: Only MCCs 4784, 5813, 7523, and 7832 are valid on EPS transactions (Reimbursement Attribute 3). *MCC 8062 is also valid for EPS transactions as of August 17, 2002. VIC Edit, Intraregional AP: Only MCCs 4784, 5814, 7523 and 7832 are valid on EPS transactions (Reimbursement Attribute 3).
Ahora: Indicates merchant’s type of business product or service. The field must contain a valid four-digit numeric Merchant Category Code (MCC). For Reimbursement Attribute 1, 2, G, or H, the entry must be 6011. National—U.S.: ●MCCs 5962, 5966, and 5967 cannot be submitted with Reimbursement Attribute A, D or J. ●MCCs 5962 or 5964 – 5969 cannot be submitted with a Requested Payment Service (RPS) of A, an Authorization Characteristic Indicator (ACI) of A or E, and a POS Entry Mode of 01 or 10. ●Only MCC 5411 is valid on Supermarket transactions (Reimbursement Attribute 4). VIC Edits: ●MCC 6010 and 6011 are invalid for original sales drafts and credit vouchers and their reversals. ●For custom payment service original purchase transactions and their reversals and Electronic Data Quality Program transactions, this field must have the same contents as in the Authorization Request (V.I.P. Field 18 converted to unpacked numeric). If multiple authorizations and/or an authorization reversal were submitted, this field must contain the Merchant Category Code from the first authorization response. ●For the CPS/Automated Fuel Dispenser custom payment service, the MCC must be 5542. ●For the CPS/ATM custom payment service, the MCC must be 6011. VIC Edit, National—Brazil: ●To qualify for the CPS/Retail-Petrol PSIRF, the MCC must be 5541. ●To qualify for the CPS/Restaurant PSIRF, the MCC must be 5812 or 5814. VIC Edit, National—U.S.: Only MCCs 7523, and 7832 are valid on EPS transactions (Reimbursement Attribute 3). VIC Edit, National—Malaysia and Macau: Only MCCs 5814, 4784 and 7832 are valid on EPS transactions (Reimbursement Attribute 3). VIC Edit, National—Hong Kong*, Australia, New Zealand, Thailand, India and Indonesia: Only MCCs 4784, 5813, 7523, and 7832 are valid on EPS transactions (Reimbursement Attribute 3). *MCC 8062 is also valid for EPS transactions as of August 17, 2002. VIC Edit, Intraregional AP: Only MCCs 4784, 5814, 7523 and 7832 are valid on EPS transactions (Reimbursement Attribute 3). See the Visa Core Rules and Visa Product and Service Rules or the Visa Merchant Data Standards Manual for valid codes. Dispute Financials, Dispute Financial Reversals The field must be the same as in the original transaction.
Razón: La edición nueva añade una restricción adicional que el campo debe ser el mismo que en la transacción original en disputas financieras, lo que modifica el significado del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 10:
`133-136` — Merchant Category Code · Ficha (note)
Antes: See the Visa Core Rules and Visa Product and Service Rules or the Visa Merchant Data Standards Manual for valid codes. Dispute Financials, Dispute Financial Reversals The field must be the same as in the original transaction.
Ahora: 
Razón: El texto antiguo especificaba que el Merchant Category Code debe coincidir con la transacción original, mientras que el nuevo texto está vacío, lo que implica una redefinición del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 11:
`150` — Settlement Flag · Ficha (description)
Antes: Indicates the service used for settlement. The field must contain 0, 3, 8, or 9 per the permitted entries shown below. If the entry is 8, the Source Currency Code must be the currency of the national settlement service. National—U.S.: The field must contain a 0, 3, or 9. National—Japan: This field must contain a 0, 8, or 9. If this field contains an 8 on purchase and credit transactions, a TCR 2 must be present. National—Mexico: This field must contain a 0, 8, or 9. If this field contains an 8 on purchase and credit transactions, a TCR 2 must be present. National—Sweden: The field must contain a 3 or 8 and a TCR 2 must be present.
Ahora: Indicates the service used for settlement. The field must contain 0, 3, 8, or 9 per the permitted entries shown below. If the entry is 8, the Source Currency Code must be the currency of the national settlement service. National—U.S.: The field must contain a 0, 3, or 9. National—Japan: This field must contain a 0, 8, or 9. If this field contains an 8 on purchase and credit transactions, a TCR 2 must be present. National—Mexico: This field must contain a 0, 8, or 9. If this field contains an 8 on purchase and credit transactions, a TCR 2 must be present. National—Sweden: The field must contain a 3 or 8 and a TCR 2 must be present. This edit will continue to be performed by the Edit Package when the Bypass Business Edits option is used during an outgoing edit run. 0 = International settlement service 3 = Clearing only international settlement 4 = Clearing only national net settlement 8 = National Net settlement service (valid only for countries with defined service) 9 = BASE II selects the appropriate settlement service based on routing and country-defined default ●The card (ARDEF) range for this account must be designated as clearing-only and reside in the same country as the source identifier. ●Entries for the Source and Destination identifiers and account number fields will be edited the same as for non-clearing-only transactions. ●Source Currency code must be valid. ●Merchant Country Code must be valid. ●Source Amount must be numeric. ●Account Number must be valid. ●Account Number Extension must be numeric. ●Acquirer Reference Number must be valid. ●Usage Code must be valid. ●Central Processing Date must be valid.
Razón: La nueva edición añade detalles específicos de validación y requisitos adicionales para el campo, como el rango de ARDEF, validación de campos y condiciones para transacciones, lo que modifica las reglas de negocio.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 12:
⚠️ `150` — Settlement Flag · Ficha (note)
Antes: This edit will continue to be performed by the Edit Package when the Bypass Business Edits option is used during an outgoing edit run. 0 = International settlement service 3 = Clearing only international settlement 4 = Clearing only national net settlement 8 = National Net settlement service (valid only for countries with defined service) 9 = BASE II selects the appropriate settlement service based on routing and country-defined default The card (ARDEF) range for this account must be designated l as clearing-only and reside in the same country as the source identifier. Entries for the Source and Destination identifiers and account l number fields will be edited the same as for non-clearing-only transactions. Source Currency code must be valid. l Merchant Country Code must be valid. l Source Amount must be numeric. l Account Number must be valid. l Account Number Extension must be numeric. l Acquirer Reference Number must be valid. l Usage Code must be valid. l Central Processing Date must be valid. l
Ahora: 
Razón: El texto nuevo está vacío, lo que indica un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 13:
152-157` — Authorization Code · Ficha (description)
Antes: A code that an issuer, its authorizing processor, or Stand-In Processing (STIP) provides to indicate approval of a transaction. The code is returned in the Authorization Response and is usually recorded on the Transaction Receipt. The field must contain a six-position Authorization Code. Allowed entries are: Spaces l A through Z l 0 through 9 l Failure to pass this edit will result in the transaction being returned.
Ahora: A code that an issuer, its authorizing processor, or Stand-In Processing (STIP) provides to indicate approval of a transaction. The code is returned in the Authorization Response and is usually recorded on the Transaction Receipt. The field must contain a six-position Authorization Code. Allowed entries are: ●Spaces ●A through Z ●0 through 9 Failure to pass this edit will result in the transaction being returned. In addition to the edit for the allowed entries that determines the validity of a transaction, the following entries indicate that the transaction is considered unauthorized by the issuer (as defined in the Visa Core Rules and Visa Product and Service Rules): ●SVCxxx (where xxx is the service code from the magnetic stripe) ●00000 (in the last five positions of the field) ^^^^^ (in the last five positions of the field) ●0000N (in the last five positions of the field) ●0000^ (in the last five positions of the field) ●0000P (in the last five positions of the field) ●0000Y (in the last five positions of the field) An ●X (in the last position of the field) (^ = space) National—U.S.: 0000Y is invalid in the last five positions for EPS, and Supermarket original sales drafts and their reversals. VIC Edit: For custom payment service original purchase transactions and their reversals and Electronic Data Quality Program transactions, the Authorization Code must be the same as in the Authorization Response (V.I.P. Field 38). If multiple authorizations and/or an authori- zation reversal were submitted, this field must contain the Authorization Code from the first authorization response. VIC Edit, National—Germany: In order to qualify for Airline IRF, the last 5 digits must not be 0000N, 0000Y, 00000, 0000^, or ^^^^^. VIC Edit, Intraregional EU and Domestic EU: In order to qualify for Airline IRF, the last 5 digits must not be 0000N, 0000Y, 00000, 0000^, ^^^^^, SVCXXX, 0000P, or X in the last position. National—U.K.: Only authorized transactions may qualify for the CNP ’94 IRF rates. International Pre-PS2000 or Hungary Domestic: A transaction will be returned or reclassified if this field contains any of these values: ^^^^^ (in the last five positions of the field) 00000 (in the last five positions of the field) 0000^ (in the last five positions of the field) 0000N (in the last five positions of the field) (^ = space)
Razón: La edición nueva incluye reglas adicionales de validación específicas para diferentes regiones y tipos de transacciones, como el uso de códigos de autorización específicos para transacciones de avión, EPS y otros servicios, lo que modifica el significado de los valores permitidos.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" pero aca ya no lleva tabulacion. Pero en la nueva version ya no lleva "Notes:", por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 14:
`152-157` — Authorization Code · Ficha (note)
Antes: In addition to the edit for the allowed entries that determines the validity of a transaction, the following entries indicate that the transaction is considered unauthorized by the issuer (as defined in the Visa Core Rules and Visa Product and Service Rules): SVCxxx (where xxx is the service code from the magnetic stripe) 00000 (in the last five positions of the field) ^^^^^ (in the last five positions of the field) 0000N (in the last five positions of the field) 0000^ (in the last five positions of the field) 0000P (in the last five positions of the field) 0000Y (in the last five positions of the field) An X (in the last position of the field) (^ = space) National—U.S.: 0000Y is invalid in the last five positions for EPS, and Supermarket original sales drafts and their reversals. VIC Edit: For custom payment service original purchase transactions and their reversals and Electronic Data Quality Program transactions, the Authorization Code must be the same as in the Authorization Response (V.I.P. Field 38). If multiple authorizations and/or an authorization reversal were submitted, this field must contain the Authorization Code from the first authorization response. VIC Edit, National—Germany: In order to qualify for Airline IRF, the last 5 digits must not be 0000N, 0000Y, 00000, 0000^, or ^^^^^. VIC Edit, Intraregional EU and Domestic EU: In order to qualify for Airline IRF, the last 5 digits must not be 0000N, 0000Y, 00000, 0000^, ^^^^^, SVCXXX, 0000P, or X in the last position. National—U.K.: Only authorized transactions may qualify for the CNP ’94 IRF rates. International Pre-PS2000 or Hungary Domestic: A transaction will be returned or reclassified if this field contains any of these values: ^^^^^ (in the last five positions of the field) 00000 (in the last five positions of the field) 0000^ (in the last five positions of the field) 0000N (in the last five positions of the field) (^ = space)
Ahora: 
Razón: El texto antiguo define valores específicos de Authorization Code que son inválidos en diferentes contextos, mientras que el texto nuevo está vacío, lo que indica que se eliminó la regla de validación para estos valores, cambiando el significado de negocio.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" pero aca ya no lleva tabulacion. Pero en la nueva version ya no lleva "Notes:", por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 15:
`168` — Reimbursement Attribute · Ficha (description)
Antes: This field must contain A through Z or 0 through 9. If 1, 2, G, or H is entered, the Merchant Category Code must be 6011 and the transaction must be a cash disbursement (TC 07, 17, 27, 37). If a 6, 7, or J is entered, the transaction cannot be a cash disbursement (TC 07, 17, 27, and 37). If a 7 is entered, the transaction cannot be an original purchased or credit voucher except in the EU region. If 8, 9, A, B, C, or J is entered, the transaction must be a sales draft (TC 05, 15, 25, 35) or a credit voucher (TC 06, 16, 26, 36). If A is entered, the transaction must be participating in a custom payment service (that is, the Authorization Characteristics Indicator cannot equal N). Regional—CEMEA: If C is entered, the MCC must be classified as an International Airline. VIC Edit, Intraregional EU and Domestic EU: C is valid for all airline MCCs for domestic and intraregional airline transactions. National—U.S.: If 4 is entered, the Merchant Category Code must be 5411. MCCs 5962, 5966, and 5967 cannot be submitted with a Reimbursement Attribute of A, D, or J. Transactions from U.S. acquirers for nonsecured electronic commerce (Moto/EC Indicator 8) must contain Reimbursement Attribute 0. VIC Edit: If A is entered, the transaction must meet all qualification criteria for the PSIRF rate. VIC Edit, National—U.S.: If 3 is entered, the Merchant Category Code must be valid for EPS transactions. VIC Edit, Regional—Asia Pacific: A 7 is not valid on original transactions (TC 05, 06, 25, 26; usage code 1). If 3 is entered, the Merchant Category Code must be valid for EPS transactions. VIC Edit, National—Malaysia, Hong Kong, Macau, Australia, New Zealand, Thailand, India, and Indonesia: If 3 is entered, the Merchant Category Code must be valid for EPS transactions.
Ahora: This field must contain A through Z or 0 through 9. If 1, 2, G, or H is entered, the Merchant Category Code must be 6011 and the transaction must be a cash disbursement (TC 07, 17, 27, 37). If a 6, 7, or J is entered, the transaction cannot be a cash disbursement (TC 07, 17, 27, and 37). If a 7 is entered, the transaction cannot be an original purchased or credit voucher except in the EU region. If 8, 9, A, B, C, or J is entered, the transaction must be a sales draft (TC 05, 15, 25, 35) or a credit voucher (TC 06, 16, 26, 36). If A is entered, the transaction must be participating in a custom payment service (that is, the Authorization Characteristics Indicator cannot equal N). Regional—CEMEA: If C is entered, the MCC must be classified as an International Airline. VIC Edit, Intraregional EU and Domestic EU: C is valid for all airline MCCs for domestic and intraregional airline transactions. National—U.S.: If 4 is entered, the Merchant Category Code must be 5411. MCCs 5962, 5966, and 5967 cannot be submitted with a Reimbursement Attribute of A, D, or J. Transactions from U.S. acquirers for nonsecured electronic commerce (Moto/EC Indicator 8) must contain Reimbursement Attribute 0. VIC Edit: If A is entered, the transaction must meet all qualification criteria for the PSIRF rate. VIC Edit, National—U.S.: If 3 is entered, the Merchant Category Code must be valid for EPS transactions. VIC Edit, Regional—Asia Pacific: A 7 is not valid on original transactions (TC 05, 06, 25, 26; usage code 1). If 3 is entered, the Merchant Category Code must be valid for EPS transactions. VIC Edit, National—Malaysia, Hong Kong, Macau, Australia, New Zealand, Thailand, India, and Indonesia: If 3 is entered, the Merchant Category Code must be valid for EPS transactions. Refer to BASE II Clearing Data Codes for Reimbursement Attribute definitions.
Razón: La nueva edición añade una referencia a la documentación BASE II Clearing Data Codes para definiciones de Reimbursement Attribute, lo que modifica el contexto de validación del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" pero aca ya no lleva tabulacion. Pero en la nueva version ya no lleva "Notes:", por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 16:
⚠️ `168` — Reimbursement Attribute · Ficha (note)
Antes: Refer to BASE II Clearing Data Codes for Reimbursement Attribute definitions.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" pero aca ya no lleva tabulacion. Pero en la nueva version ya no lleva "Notes:", por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 17:
`38-48` — Acquirer Reference Number— Film Locator · Ficha (name)
Antes: Film Locator
Ahora: Acquirer Reference Number— Film Locator
Razón: El campo se redefinio para incluir el nombre completo del campo en lugar de solo su identificador.
Obs: Todo Ok

Caso 18:
`92-116` — Merchant Name · Ficha (description)
Antes: Name of the merchant in the original transaction. The first position in this field cannot be a space. VIC Edit: Entries must not exceed 25 characters. For entries less than 25, space-fill after the last character. Refer to the Visa Core Rules and Visa Product and Service Rules for any special requirements regarding the use of the Merchant Name field.
Ahora: Name of the merchant in the original transaction. The first position in this field cannot be a space. VIC Edit: Entries must not exceed 25 characters. For entries less than 25, space-fill after the last character. Refer to the Visa Core Rules and Visa Product and Service Rules for any special requirements regarding the use of the Merchant Name field. Some airline fee programs may require the original ticket number (ticket identifier) or the ancillary service description in positions 13 through 25 of the merchant name. VisaPhone transactions (MCC 4815) must be in the following format: Dispute Response Financials The field must be the same as in the original transaction unless a correction is required to resolve a dispute financial. Dispute Financials, Reversals The entry must be the same as in the original transaction.
Razón: La nueva edición añade restricciones específicas para programas de tarifas aéreas y transacciones VisaPhone, modificando las reglas de negocio para el campo Merchant Name.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 19:
`92-116` — Merchant Name · Ficha (note)
Antes: Some airline fee programs may require the original ticket number (ticket identifier) or the ancillary service description in positions 13 through 25 of the merchant name. VisaPhone transactions (MCC 4815) must be in the following format: Dispute Response Financials The field must be the same as in the original transaction unless a correction is required to resolve a dispute financial. Dispute Financials, Reversals The entry must be the same as in the original transaction.
Ahora: 
Razón: El texto antiguo especifica que VisaPhone transactions (MCC 4815) deben seguir un formato particular en el campo Merchant Name, mientras que el texto nuevo está vacío, lo que implica una redefinición del campo o una condición de negocio que cambió.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 20:
⚠️ `26-37` — Installment Payment Interest Amount · Ficha (description)
Antes: This field must contain the installment payment interest amount. This field must contain all zeros, when the value of payment indicator in positions 20–21 contains one of the following: CC l CO l CR l PA l For cash disbursement, Visa will default to zeros.
Ahora: This field must contain the installment payment interest amount. This field must contain all zeros, when the value of payment indicator in positions 20–21 contains one of the following: ●CC ●CO ●CR ●PA For cash disbursement, Visa will default to zeros.
Razón: El texto describe lo mismo pero con formato de lista más claro y sin espacios en los códigos.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.

Caso 21:
⚠️ `70-75` — Deferred Cardholder Billing Date · Ficha (description)
Antes: This field will contain the deferred cardholder billing date in the yymmdd format, where: yy (Year) = 00–99 l mm (Month) = 01–12 l dd (Day) = 01–31 l This field must be present when the payment indicator in positions 20– 21 contains one of the following values: AD l CD l PA l Additionally, this field must not be submitted earlier than the CPD. For all other values of Payment Indicator in positions 20–21, this field must contain all zeros.
Ahora: This field will contain the deferred cardholder billing date in the yymmdd format, where: ●yy (Year) = 00–99 ●mm (Month) = 01–12 ●dd (Day) = 01–31 This field must be present when the payment indicator in positions 20– 21 contains one of the following values: ●AD ●CD ●PA Additionally, this field must not be submitted earlier than the CPD. For all other values of Payment Indicator in positions 20–21, this field must contain all zeros.
Razón: El texto describe el mismo contenido pero con formato de lista y puntos para mejorar la legibilidad, sin cambios en el significado o reglas de negocio.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.

Caso 22:
20-31` — Amount Base of Add Value Tax to Return · Grilla (Position)
Antes: 88–95
Ahora: 20–31
Razón: El rango de posiciones del campo cambia de 88-95 a 20-31, lo que redefine su posición en el mensaje y afecta el cálculo del valor de negocio.
Obs: Ok

Caso 23:
`20-31` — Amount Base of Add Value Tax to Return · Grilla (Field Length)
Antes: 8
Ahora: 12
Razón: El campo de longitud cambia de 1 a 12 bytes, lo que implica un cambio en la cantidad de datos que se espera para el valor de la tarjeta de crédito en Colombia.
Obs: Ok

Caso 24:
`20-31` — Amount Base of Add Value Tax to Return · Ficha (positions)
Antes: 88–95
Ahora: 20–31
Razón: El rango de posiciones del campo cambia de 88-95 a 20-31, lo que redefine el layout del mensaje y afecta la interpretación del campo en el formato de intercambio.
Obs: Ok

Caso 25:
`20-31` — Amount Base of Add Value Tax to Return · Ficha (length)
Antes: 8
Ahora: 12
Razón: El campo 'length' cambia de 8 a 12 bytes, lo que implica un cambio en la longitud válida del campo de valor de la tarjeta, afectando la estructura de datos y el significado del mensaje.
Obs: Ok

Caso 26:
`3` — Transaction Code Qualifier · Ficha (description)
Antes: The field must contain one of these values: 0 = Default 1 = Account Funding 2 = Original Credit
Ahora: The field must contain one of these values: 0 = Default 1 = Account Funding 2 = Original Credit This edit will continue to be performed by the Edit Package when the Bypass Business Edits option is used during an outgoing edit run.
Razón: La nueva edición añade una condición adicional sobre el uso del Edit Package y la opción Bypass Business Edits, lo que modifica el comportamiento del campo en situaciones específicas.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 27:
⚠️ `3` — Transaction Code Qualifier · Ficha (note)
Antes: This edit will continue to be performed by the Edit Package when the Bypass Business Edits option is used during an outgoing edit run.
Ahora: 
Razón: El texto nuevo está vacío, lo que sugiere un artefacto de extracción en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 28:
`32-43` — Consumption Tax Amount · Grilla (Position)
Antes: 96–104
Ahora: 32–43
Razón: El rango de posición del campo de Consumo de Impuesto cambió de 96-104 a 32-43, lo que implica una redefinición del layout del mensaje.
Obs: Ok

Caso 29:
`32-43` — Consumption Tax Amount · Grilla (Field Length)
Antes: 9
Ahora: 12
Razón: El campo de longitud del monto de impuesto de consumo cambió de 1 a 2 bytes, lo que implica un cambio en la validación de datos y el rango de valores permitidos.
Obs: Ok

Caso 30:
`32-43` — Consumption Tax Amount · Ficha (positions)
Antes: 96–104
Ahora: 32–43
Razón: El rango de posiciones del campo de impuesto de consumo cambió de 96-104 a 32-43, lo que redefine su ubicación en el mensaje.
Obs: Ok

Caso 31:
`32-43` — Consumption Tax Amount · Ficha (length)
Antes: 9
Ahora: 12
Razón: El campo 'length' cambia de 1 a 2 bytes, lo que implica un cambio en la longitud del campo de consumo de impuestos, afectando la validación y estructura de los mensajes.
Obs: Ok

Caso 32:
⚠️ `32-43` — Consumption Tax Amount · Ficha (description)
Antes: Optional. This field will contain the National Consumption Tax and is applicable for the following goods and services. Mobile Services l Motor vehicles, boats, airplane l Sale of food and beverages l This field should be right-justified. Two decimal places are implied. This field should be zero-filled when the information is not present. Outgoing: The Edit Package will insert zeros in this field if the value is not numeric.
Ahora: Optional. This field will contain the National Consumption Tax and is applicable for the following goods and services. ●Mobile Services ●Motor vehicles, boats, airplane ●Sale of food and beverages This field should be right-justified. Two decimal places are implied. This field should be zero-filled when the information is not present.
Razón: El texto se reescribió para eliminar los puntos y usar viñetas, manteniendo el mismo significado.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 33:
`44-55` — Add Value Tax Amount · Grilla (Position)
Antes: 105–113
Ahora: 44–55
Razón: El rango de posición del campo cambia de 105-113 a 44-55, lo que redefine su ubicación en el mensaje y afecta el formato de intercambio.
Obs: Ok

Caso 34:
`44-55` — Add Value Tax Amount · Grilla (Field Length)
Antes: 9
Ahora: 12
Razón: El campo de longitud cambia de 1 a 12 bytes, lo que implica un cambio en la cantidad de datos que se procesa, afectando la validación y el formato del mensaje.
Obs: Ok

Caso 35:
`44-55` — Add Value Tax Amount · Ficha (positions)
Antes: 105–113
Ahora: 44–55
Razón: El rango de posiciones del campo cambia de 105-113 a 44-55, lo que redefine el layout del mensaje y afecta la estructura de datos.
Obs: Ok

Caso 36:
`44-55` — Add Value Tax Amount · Ficha (length)
Antes: 9
Ahora: 12
Razón: El campo 'length' cambia de 9 a 12 bytes, lo que implica un cambio en la longitud válida del campo de valor fiscal, afectando la estructura de datos y el significado del mensaje.
Obs: Ok

Caso 37:
`139` — Net/Gross Flag · Ficha (description)
Antes: Indicates net or gross amount. The entry must be numeric.
Ahora: Indicates net or gross amount. The entry must be numeric. 1, 2, 8 or 9 must be set. If not used, set 1 (no space or 0).
Razón: La nueva edición especifica que deben establecerse valores 1, 2, 8 o 9, y si no se usa el campo debe ser 1 (sin espacio o 0), lo que modifica la regla de negocio respecto a los valores permitidos.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 38:
`139` — Net/Gross Flag · Ficha (note)
Antes: 1, 2, 8 or 9 must be set. If not used set 1 (no space or 0).
Ahora: 
Razón: La edición vieja especificaba que debe ser 1, 2, 8 o 9, mientras que la nueva está vacía, lo que implica una redefinición del campo sin condiciones válidas.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 39:
`160-167` — Acquirer's Invoice Amount · Ficha (description)
Antes: The net value of the transaction after applying the Interchange Reimbursement Fee. The entry must be numeric.
Ahora: The net value of the transaction after applying calculated Interchange Reimbursement Fee Incoming: The entry must be zero-filled. Outgoing: The field will contain the net value of the transaction after applying the Interchange Reimbursement Fee calculated by clearing.
Razón: El texto nuevo especifica que el campo debe ser cero rellenado para entradas entrantes y contiene el valor calculado para salidas, mientras que la versión anterior solo requería ser numérico.
Obs: Ok

Caso 40:
`26-33` — Net Sales Amount · Ficha (description)
Antes: This field must contain the sales amount of the goods and service before tax and mailing charges. The entry must be numeric.
Ahora: This field must contain the sales amount of the goods and service before tax and mailing charges. The entry must be numeric. If the Tax and Mailing Charge is zero, this value should be equal to TCR 0 Source Amount.
Razón: La nueva edición añade una condición específica que el valor debe coincidir con el TCR 0 Source Amount si el Tax and Mailing Charge es cero, lo que modifica la lógica de negocio.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 41:
`26-33` — Net Sales Amount · Ficha (note)
Antes: If the Tax and Mailing Charge is zero, this value should be equal to TCR 0 Source Amount.
Ahora: 
Razón: La edición nueva elimina la condición de que el valor debe ser igual al TCR 0 Source Amount cuando el Tax and Mailing Charge es cero, lo que cambia la regla de negocio.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 42:
`34-41` — Tax and Mailing Charge · Ficha (description)
Antes: Tax and mailing charge portion of transaction. The entry must be numeric and may be zeros.
Ahora: Tax and mailing charge portion of transaction. The entry must be numeric and may be zeros. * TCR 2 Net Sales Amount (position 26–33) + Tax and Mailing Charge (34–41) = TCR 0 Source Amount (= Destination Amount).
Razón: La nueva edición añade una regla de negocio que relaciona TCR 2 Net Sales Amount con Tax and Mailing Charge para calcular TCR 0 Source Amount, modificando la lógica de validación.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 43:
`34-41` — Tax and Mailing Charge · Ficha (note)
Antes: * TCR 2 Net Sales Amount (position 26–33) + Tax and Mailing Charge (34–41) = TCR 0 Source Amount (= Destination Amount).
Ahora: 
Razón: El texto antiguo define una relación matemática entre campos que ahora está vacío, lo que implica que la regla de negocio cambió significativamente.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 44:
`42-58` — Sales Draft Reference Number · Ficha (description)
Antes: Reference number of the sales draft. The entry must be numeric.
Ahora: Reference number of the sales draft. The entry must be numeric. First 4 byte = MMDD. May copy from TCR 0 Purchase Date (position 58– 61) to first 4 byte.
Razón: La nueva edición especifica que los primeros 4 bytes deben ser MMDD y puede copiarse de la fecha de compra en TCR 0, lo que redefine la validación del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 45:
⚠️ `42-58` — Sales Draft Reference Number · Ficha (note)
Antes: First 4 byte = MMDD. May copy from TCR 0 Purchase Date (position 58–61) to first 4 byte.
Ahora: 
Razón: El texto nuevo está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 46:
⚠️ `149` — Spend Qualified Indicator · Ficha (description)
Antes: This field indicates whether the account is Spend Qualified or not. VIC Edit: Visa will include the appropriate value in this field. This field will contain; B (Base spend assessment threshold defined by Visa has been met.) l Q (Spend assessment threshold defined by Visa has been met.) l N (Spend assessment threshold defined by Visa has not been met.) l Space (Spend processing does not apply (Not applicable).) l J Not Qualified Tier 5 l K Not Qualified Tier 4 l L Not Qualified Tier 3 l M Not Qualified Tier 2 l R Qualified Tier 2 l S Qualified Tier 3 l T Qualified Tier 4 l U Qualified Tier 5 l V Qualified Tier 6 l W Qualified Tier 7 l 1 Tier 1 - Spend assessment threshold defined by Visa has been met l 2 Tier 2 - Spend assessment threshold defined by Visa has been met l 3 Tier 3 - Spend assessment threshold defined by Visa has been met l 4 Tier 4 - Spend assessment threshold defined by Visa has been met l 5 Tier 5 - Spend assessment threshold defined by Visa has been met l Acquirers can choose to receive spend qualified indicator reclassifi­ cations by submitting nonspace values in this field. Acquirers that choose not to receive spend qualified indicator reclassifi­ cations should submit space in this field.
Ahora: This field indicates whether the account is Spend Qualified or not. VIC Edit: Visa will include the appropriate value in this field. This field will contain; ●B (Base spend assessment threshold defined by Visa has been met.) ●Q (Spend assessment threshold defined by Visa has been met.) ●N (Spend assessment threshold defined by Visa has not been met.) ●Space (Spend processing does not apply (Not applicable).) ●J Not Qualified Tier 5 ●K Not Qualified Tier 4 ●L Not Qualified Tier 3 ●M Not Qualified Tier 2 ●R Qualified Tier 2 ●S Qualified Tier 3 ●T Qualified Tier 4 ●U Qualified Tier 5 ●V Qualified Tier 6 ●W Qualified Tier 7 ●1 Tier 1 - Spend assessment threshold defined by Visa has been met ●2 Tier 2 - Spend assessment threshold defined by Visa has been met ●3 Tier 3 - Spend assessment threshold defined by Visa has been met ●4 Tier 4 - Spend assessment threshold defined by Visa has been met ●5 Tier 5 - Spend assessment threshold defined by Visa has been met Acquirers can choose to receive spend qualified indicator reclassifi- cations by submitting nonspace values in this field. Acquirers that choose not to receive spend qualified indicator reclassifi- cations should submit space in this field.
Razón: El texto solo cambió los puntos de lista de los valores con asteriscos en lugar de puntos y corrigió un espacio extra en 'reclassifi- cations' para mantener la coherencia en el formato de texto.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras

Caso 47:
`157` — Applied Special Service · Ficha (description)
Antes: This field will contain VDCAP Indicator from acquirer. This field will contain a value of 1 (VDCAP). 1 = VDCAP Space = Default
Ahora: This field will contain the Digital Commerce Authentication Program (DCAP) Indicator from acquirer. This field will contain a value of 1 (DCAP). 1 = DCAP Space = Default
Razón: El campo se redefinio de VDCAP a DCAP, cambiando el significado técnico y el valor de negocio.
Obs: Ok

Caso 48:
⚠️ `77-146` — Message Text · Ficha (name)
Antes: Message Text Field for Reason Code 0300
Ahora: Message Text
Razón: El texto describe el mismo concepto pero con una redacción más simple y directa, eliminando detalles específicos como el código de razón.
Obs: Ok

Caso 49:
`77-146` — Message Text · Ficha (description)
Antes: This field can be used for a text message for transactions with a Reason Code of 0300. This field is used only in Brazil and Canada Bill Payment Service.
Ahora: This field can be used for a freeform text message or for required information. In a Funds Disbursement Reason Code 0300 transaction (Bill Payment Service for Brazil and Canada only), this field must not contain all spaces. In a Funds Disbursement Reason Code 5220 or 5230, the message text contains transaction reconciliation data for the Commercial Enhanced Data Program (CEDP). Refer to the Commercial Enhanced Data Program Guide U.S. – Visa Commercial Solutions for further details.
Razón: El texto define nuevas reglas de uso para el campo en transacciones específicas (Reason Code 0300, 5220, 5230) y establece requisitos adicionales como evitar espacios en blanco y contenido de CEDP, lo que cambia el significado operativo del campo.
Obs: Ok

Caso 50:
`4` — Transaction Component Sequence Number · Ficha (name)
Antes: Transaction Code Qualifier Number
Ahora: Transaction Component Sequence Number
Razón: El campo se redefinio de 'Transaction Code Qualifier Number' a 'Transaction Component Sequence Number', cambiando su significado técnico y de negocio.
Obs: Ok

Caso 51:
`21-30` — Merchant Verification Value · Ficha (description)
Antes: This field will contain the merchant verification value (MVV) that was assigned to the merchant.
Ahora: This field will contain the merchant verification value (MVV) that was assigned to the merchant. ●Values: A-F, 0-9 ●Default value: spaces
Razón: La nueva edición añade reglas de valores (A-F, 0-9) y un valor predeterminado (espacios), modificando las reglas de negocio del campo.
Obs: Me parece raro que me digas que no aparece, si en verdad aparece esos valores. solo que lo has clasificado como un chunk distinto. Justo el Caso 52

Caso 52:
`21-30` — Merchant Verification Value · Ficha (values)
Antes: A-F, 0-9 l Default value: spaces l
Ahora: 
Razón: El valor predeterminado cambió de espacios a vacío, lo que implica una redefinición del comportamiento del campo.
Obs: Me parece raro que me digas que no aparece, si en verdad aparece esos valores. solo que lo has clasificado como un chunk distinto. justo el caso 51

Caso 53:
⚠️ `31-33` — Fee Program Indicator · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a listing of the fee program indicators.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 54:
`100` — Authorization Characteristics Indicator · Ficha (description)
Antes: Code used by the acquirer to request CPS qualification as returned in the original authorization response.
Ahora: Code used by the acquirer to request CPS qualification as returned in the original authorization response. See BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization.
Razón: La nueva descripción incluye información adicional sobre los códigos válidos y su población basada en la autorización crediticia, lo que modifica el significado del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 55:
⚠️ `100` — Authorization Characteristics Indicator · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 56:
`101` — POS Terminal Capability · Ficha (description)
Antes: Indicates the capability of the point-of-sale (POS) terminal to obtain an authorization and process transaction data.
Ahora: Indicates the capability of the point-of-sale (POS) terminal to obtain an authorization and process transaction data. See BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization.
Razón: La nueva edición añade información sobre los códigos válidos y la lógica de llenado, modificando el significado del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 57:
⚠️ `101` — POS Terminal Capability · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 58:
`102` — Cardholder ID Method · Ficha (description)
Antes: Indicates method used to identify cardholder (e.g., signature or Personal Identification Number [PIN]).
Ahora: Indicates method used to identify cardholder (e.g., signature or Personal Identification Number [PIN]). See BASE II Clearing Data Codes for a list of valid codes. Space-filled for credits.
Razón: La nueva edición añade información sobre los códigos válidos y el comportamiento para créditos, lo que modifica el significado del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 59:
⚠️ `102` — Cardholder ID Method · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes. Space-filled for credits.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 60:
⚠️ `129-130` — Electronic Commerce Goods Indicator · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications for a list of valid values.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.: 

Caso 61:
⚠️ `131-133` — Fee Program Indicator · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.: 

Caso 62:
⚠️ `134` — Service Development Field · Ficha (note)
Antes: Please see BASE II Clearing Interchange Formats for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 63:
⚠️ `135` — Account Selection · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications for a list of valid values.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 64:
`136` — POS Environment · Ficha (description)
Antes: A recurring transaction indicator, indicating that the cardholder and merchant have agreed to periodic billing for goods and services, such as utility bills, Internet connection, and magazine subscriptions.
Ahora: A recurring transaction indicator, indicating that the cardholder and merchant have agreed to periodic billing for goods and services, such as utility bills, Internet connection, and magazine subscriptions. See BASE II Clearing Data Codes for a list of valid codes. Space-filled for credits.
Razón: La nueva edición añade información sobre códigos válidos y especifica que se rellena con espacios para créditos, lo que modifica el comportamiento del campo en términos de validación y uso.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 65:
⚠️ `136` — POS Environment · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes. Space-filled for credits.
Ahora: 
Razón: El texto nuevo está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 66:
`15-16` — POS Entry Mode · Ficha (description)
Antes: A V.I.P. System field indicating the method by which a point-of-transaction terminal obtains and transmits the cardholder information necessary to complete a Transaction.
Ahora: A V.I.P. System field indicating the method by which a point-of-transaction terminal obtains and transmits the cardholder information necessary to complete a Transaction. See Full Service POS Online Messages Technical Specifications for a list of values. Populated based on Credit Authorization.
Razón: La nueva edición añade información sobre los valores válidos y el comportamiento de llenado del campo, modificando su significado en términos de negocio.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 67:
⚠️ `15-16` — POS Entry Mode · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications for a list of values. Populated based on Credit Authorization.
Ahora: 
Razón: El texto nuevo está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 68:
⚠️ `167` — Spend Qualified Indicator · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: 

Caso 69:
⚠️ `168` — CAVV Results Code · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: 

Caso 70:
⚠️ `32-39` — Terminal ID · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: No logro encontrar esta diff

Caso 71:
`40` — Mail/Phone/Electronic Commerce and Payment Indicator · Ficha (description)
Antes: Indicates transaction performed by mail order, telephone, or electronic commerce. codes.
Ahora: Indicates transaction performed by mail order, telephone, or electronic commerce. See BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization.
Razón: La nueva descripción incluye que los códigos son válidos según BASE II Clearing Data Codes y que el campo se popula basado en la autorización de crédito, lo que modifica el significado del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 72:
⚠️ `40` — Mail/Phone/Electronic Commerce and Payment Indicator · Ficha (note)
Antes: Populated based on Credit Authorization. Please see BASE II Clearing Data Codes for a list of valid
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 73:
`42` — AVS Response Code · Ficha (description)
Antes: Contains the response to an Address Verification Service (AVS) request, indicating matches or discrepancies between addresses and ZIP codes.
Ahora: Contains the response to an Address Verification Service (AVS) request, indicating matches or discrepancies between addresses and ZIP codes. See BASE II Clearing Data Codes for a list of valid codes. Space-filled for credits.
Razón: La nueva edición añade información sobre los códigos válidos y el relleno espaciado para créditos, lo que modifica el significado del campo en términos de validación y uso.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 74:
⚠️ `42` — AVS Response Code · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes. Space-filled for credits.
Ahora: 
Razón: El texto nuevo está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 75:
⚠️ `43` — Authorization Source Code · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 76:
⚠️ `44` — Purchase Identifier Format · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of values.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 77:
`5-8` — Capture Date · Ficha (description)
Antes: The date when the merchant intends to process the capture file (MMDD) in the merchant local time.
Ahora: The date when the merchant intends to process the capture file (MMDD) in the merchant local time. Space-filled for credits.
Razón: La nueva edición añade que el campo está rellenado con espacios para créditos, lo que modifica el comportamiento del campo en el contexto de transacciones.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.  

Caso 78:
`72-73` — Point-of-Service Condition Code · Ficha (description)
Antes: Code identifying transaction conditions at the point of sale or point of service. Can be used to identify a type of original, or subsequent, transaction.
Ahora: Code identifying transaction conditions at the point of sale or point of service. Can be used to identify a type of original, or subsequent, transaction. See Full Service POS Online Messages Technical Specifications. Populated based on Credit Authorization.
Razón: La nueva edición añade información sobre cómo se popula el campo y referencia a especificaciones técnicas, lo que modifica el significado operativo del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.  

Caso 79:
⚠️ `72-73` — Point-of-Service Condition Code · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications. Populated based on Credit Authorization.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.  

Caso 80:
⚠️ `74-79` — Processing Code · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications for a list of values. Populated based on Credit Authorization.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 81:
⚠️ `80-83` — Network ID · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 82:
⚠️ `84-85` — Authorization Response Code · Ficha (note)
Antes: Please see Full Service POS Online Messages Technical Specifications. Populated based on Credit Authorization.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 83:
`9-14` — Authorization Code · Ficha (description)
Antes: A code that an issuer, its authorizing processor, or Stand-In Processing (STIP) provides to indicate approval of a transaction. The code is returned in the Authorization Response and is usually recorded on the Transaction Receipt.
Ahora: A code that an issuer, its authorizing processor, or Stand-In Processing (STIP) provides to indicate approval of a transaction. The code is returned in the Authorization Response and is usually recorded on the Transaction Receipt. See BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization. The authorization code must be managed in accordance with the requirements of the relevant card scheme.
Razón: La nueva edición añade requisitos específicos sobre la gestión del código de autorización según los requisitos del esquema de tarjeta, lo que modifica la regla de negocio.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.  

Caso 84:
⚠️ `9-14` — Authorization Code · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes. Populated based on Credit Authorization.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 85:
`91-92` — Product ID · Ficha (description)
Antes: This field will contain Product ID.
Ahora: This field will contain Product ID. Space-filled for credits.
Razón: La nueva edición especifica que el campo se rellena con espacios para créditos, lo que modifica el comportamiento del campo en términos de formato de datos.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 86:
`93-98` — Program ID · Ficha (description)
Antes: Program identifier. Available for US domestic transactions when provided by issuer.
Ahora: Program identifier. Available for US domestic transactions when provided by issuer. Space-filled for credits.
Razón: La nueva edición añade que el campo se rellena con espacios para créditos, lo que modifica el comportamiento del campo en transacciones.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 87:
`99` — CVV2 Result Code · Ficha (description)
Antes: Card Verification Value 2 (CVV2) is the verification result for card-not-present transactions and also for card-present CVV2 verifi­ cation-only requests.
Ahora: Card Verification Value 2 (CVV2) is the verification result for card-not-present transactions and also for card-present CVV2 verifi- cation-only requests. Space-filled for credits and cash disbursement transactions. See BASE II Clearing Data Codes for a list of valid codes.
Razón: La nueva edición añade información sobre transacciones de crédito y desembolso que no estaba en la versión anterior, modificando el significado del campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 88:
⚠️ `99` — CVV2 Result Code · Ficha (note)
Antes: Space-filled for credits and cash disbursement transactions. Please see BASE II Clearing Data Codes for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 89:
`17-18` — Payment Mode · Ficha (description)
Antes: This field will contain a code indicating the type of installment payments.
Ahora: This field will contain a code indicating the type of installment payments. For valid values, see BASE II Clearing Data Codes.
Razón: La nueva edición añade una referencia a los códigos válidos en BASE II, lo que modifica la información sobre los valores permitidos para el campo.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 90:
⚠️ `17-18` — Payment Mode · Ficha (note)
Antes: For valid values,see BASE II Clearing Data Codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.
 

Caso 91:
⚠️ `8` — Number of Bonus Payments · Ficha (note)
Antes: For valid values, see BASE II Clearing Data Codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 92:
⚠️ `9` — Bonus Month Sign · Ficha (note)
Antes: For valid values, see BASE II Clearing Data Codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 93:
⚠️ `48` — Local Tax Included · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción. 

Caso 94:
⚠️ `61` — National Tax Included · Ficha (note)
Antes: Please see BASE II Clearing Data Codes for a list of valid codes.
Ahora: 
Razón: El texto en la edición nueva está vacío, lo que sugiere un artefacto de extracción de PDF en lugar de un cambio real de contenido.
Obs: Como comente, no es que haya una nueva resitrccion es que la restricción que indicas estaba antes en un "Notes" y con tabulación. Pero en la nueva version ya no lleva "Notes:" ni tampoco esta en una tabulación, por eso pudiera entenderse que es otro chunk. Pero siempre estuvo ahi esa resitrcción.

Caso 95:
59-78` — Tax Document Type · Ficha (description)
Antes: This field will contain the Tax Document Type in OCT transactions in Latin America. Values: Country Tax Field Comments Identifier Peru RUC Registro Tag 05- Business tax Unico de Merchant VAT identification Contrib­ Registration/ uyentes Single Business Reference Number DNI Documento Tag 06- Individual tax Nacional de Customer VAT identification Identidad Registration Number
Ahora: This field will contain the Tax Document Type in OCT transactions in Latin America. Values: Country Tax Field Comments Identifier Colombia NIT Numero de Tag 05- Business tax Identifi- Merchant VAT identification cacion Registration/ Tributaria Single Business Reference Number CC, CE, Cedula de Tag 06- Individual tax or PASS Ciudadania Customer VAT identification Registration Number Peru RUC Registro Tag 05- Business tax Unico de Merchant VAT identification Contrib- Registration/ uyentes Single Business Reference Number DNI Documento Tag 06- Individual tax Nacional de Customer VAT identification Identidad Registration Number
Razón: El cambio incluye nuevas identificaciones de país (Colombia y Perú) y diferentes formatos de documentos tributarios, lo que altera los valores válidos para el campo Tax Document Type.
Obs: Esta Ok, en realidad es porque el mismo documento anterior esta muy descuadrado, pero si se entiende bien como esta en la nueva version. Todo Ok.

Caso 96:
`73-108` — Mastercard Transaction Link Identifier/Gateway Life Cycle Trace Identifier · Grilla (Position)
Antes: 74-109
Ahora: 73-108
Razón: El rango de posiciones cambió de 74-109 a 73-108, lo que afecta el tamaño del campo y su definición en el formato.
Obs: No ha contemplado todos los campos que dejaron de ser reservados como comenté antes. Antes era:
64-73 10 AN Mastercard - Service Location Postal Code
74-109 36 AN Mastercard Transaction Link Identifier/Gateway Life Cycle Trace Identifier

Ahora es: 
64-72 9 AN Reserved
73-108 36 AN Mastercard Transaction Link Identifier/Gateway Life Cycle Trace
Identifier
109 1 AN Reserved

Por eso es que no detecta todos y solo detecta a 73-108` — Mastercard Transaction Link Identifier/Gateway Life Cycle Trace Identifier. Pero debería identificar a los demás.

Caso 97:
`73-108` — Mastercard Transaction Link Identifier/Gateway Life Cycle Trace Identifier · Ficha (positions)
Antes: 74-109
Ahora: 73-108
Razón: El rango de posiciones del campo cambió de 74-109 a 73-108, lo que afecta el tamaño y el rango válido del campo en el formato de mensaje.
Obs: No ha contemplado todos los campos que dejaron de ser reservados como comenté antes. Antes era:
64-73 10 AN Mastercard - Service Location Postal Code
74-109 36 AN Mastercard Transaction Link Identifier/Gateway Life Cycle Trace Identifier

Ahora es: 
64-72 9 AN Reserved
73-108 36 AN Mastercard Transaction Link Identifier/Gateway Life Cycle Trace
Identifier
109 1 AN Reserved

Por eso es que no detecta todos y solo detecta a 73-108` — Mastercard Transaction Link Identifier/Gateway Life Cycle Trace Identifier. Pero debería identificar a los demás.

Caso 98:
`61-80` — Tax Document Type · Ficha (description)
Antes: This field will contain the Tax Document Type in OCT transactions in Latin America. Field Comments Identifier Peru RUC Registro Tag 05- Business tax Unico de Merchant VAT identification Contrib­ Registration/ uyentes Single Business Reference Number DNI Documento Tag 06- Individual tax Nacional de Customer VAT identification Identidad Registration Number
Ahora: This field will contain the Tax Document Type in OCT transactions in Latin America. Field Comments Identifier Colombia NIT Numero do Tag 05- Business tax Identifi- Merchant VAT identification cacion Registration/ Tributaria Single Business Reference Number CC, CE, Cedula de Tag 06- Individual tax or PASS Ciudadania Customer VAT identification Registration Number Peru RUC Registro Tag 05- Business tax Unico de Merchant VAT identification Contrib- Registration/ uyentes Single Business Reference Number DNI Documento Tag 06- Individual tax Nacional de Customer VAT identification Identidad Registration Number
Razón: El campo de Tax Document Type ahora incluye diferentes identificadores para Colombia (NIT) y Perú (RUC) en lugar de solo Perú, lo que cambia el significado de negocio al definir el formato de identificación fiscal según el país.
Obs: Esta Ok, en realidad es porque el mismo documento anterior esta muy descuadrado, pero si se entiende bien como esta en la nueva version. Todo Ok.

Caso 98:
⚠️ `153-164` — Retrieval Reference Number · Ficha (description)
Antes: Contains a number that is used with other data elements as a key to identify and track all messages related to a given cardholder transaction, that is, to a given transaction set. These sets are: Authorization l Purchase l Merchandise return l Cash disbursement (manual cash) l The ISO field is 37.
Ahora: Contains a number that is used with other data elements as a key to identify and track all messages related to a given cardholder transaction, that is, to a given transaction set. These sets are: ●Authorization ●Purchase ●Merchandise return ●Cash disbursement (manual cash) The ISO field is 37.
Razón: El texto describe lo mismo pero reemplaza los puntos con guiones circulares para los tipos de transacciones, sin cambiar el significado o valores válidos.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.