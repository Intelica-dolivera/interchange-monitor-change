Caso 1 
⚠️ Código `1` — columna *Usage Use to indicate that the transaction does not originate at an unattended terminal.*
Antes: Use to indicate that the transaction:
l
Is less than US$40, or local currency
equivalent.
l
Is not authorized.
l
Examples of a Type A UAT transaction are:
Has no cardholder verification performed.
l
l
l
l
Parking garage fee
Road toll
Motion picture theater admission
Magnetic stripe telephone call
Ahora: Use to indicate that the transaction:
●Is less than US$40, or local currency
equivalent.
●Is not authorized.
●Has no cardholder verification performed.
Examples of a Type A UAT transaction are:
●Parking garage fee
●Road toll
●Motion picture theater admission
●Magnetic stripe telephone call
Razón: El texto se reorganizó para mejorar la estructura con marcado de puntos y listas, pero el significado y los valores no cambiaron.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.

Caso 2 
⚠️ Código `2` — columna *Usage Use to indicate that the transaction does not originate at an unattended terminal.*
Antes: Use to indicate that the transaction:
l
Is authorized.
l
Examples of a Type C UAT transaction are:
Has PIN verification performed.
l
ATM
l
Fuel purchase with PIN
Ahora: Use to indicate that the transaction:
●Is authorized.
●Has PIN verification performed.
Examples of a Type C UAT transaction are:
●ATM
●Fuel purchase with PIN
Razón: El texto describe lo mismo pero con formato de lista diferente y orden de ejemplos ajustado.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.

Caso 3 
Código `BULGARIA` — columna *ISO Currency Name*
Antes: Bulgarian Lev
Ahora: EuroS
Razón: El texto anterior 'Bulgarian Lev' indica la moneda de Bulgaria, mientras que 'EuroS' es el nombre de la moneda en uso actual, cambiando el significado de negocio.
Obs: Ok

Caso 4 
Código `BULGARIA` — columna *ISO Alpha Currency Code*
Antes: BGN
Ahora: EUR
Razón: El código de moneda cambió de BGN a EUR, lo que representa un cambio real en el valor de negocio para Bulgaria.
Obs: Ok

Caso 5 
Código `BULGARIA` — columna *ISO Numeric Currency Code*
Antes: 975
Ahora: 978
Razón: El código ISO Numeric Currency Code cambió de 975 a 978, lo que altera el valor de negocio del código de moneda.
Obs: Ok

Caso 6 
Código `CROATIA` — columna *ISO Currency Name*
Antes: Euro
Ahora: EuroS
Razón: El texto cambió de 'Euro' a 'EuroS', lo que altera el significado del código de moneda en el contexto de Visa.
Obs: Ok

Caso 7 
Código `CROATIA` — columna *ISO Alpha Currency Code*
Antes: Euro
Ahora: EUR
Razón: El código de moneda cambió de 'Euro' a 'EUR', que es el código ISO estándar para la moneda oficial de Croacia.
Obs: Ok

Caso 8 
Código `ACCOUNT SCREEN CLEARING FILE (ASCF)` — columna *Definition*
Antes: The Account Screen Clearing File (ASCF) provides global clearing transaction
protection for listed accounts, including below-floor-limit transactions, force-
posted transactions and card-not-present transactions. The file is an extract
of negatively listed accounts from the ASAF that Visa references in clearing
when the issuer participates in Account Screen All Respond and Clearing
Return functionality.
Ahora: Provides global clearing transaction protection for listed accounts, including
below-floor-limit transactions, force-posted transactions, and card-not-
present transactions. The file is an extract of negatively listed accounts from
the Account Screen Authorization File (ASAF) that Visa references in Clearing
when the Issuer participates in Account Screen All Respond and Clearing
Return functionality.
Razón: El cambio modifica el nombre del archivo ASAF a Account Screen Authorization File (ASAF) y ajusta la descripción de la función de clearing, lo que implica una diferencia en el significado técnico del proceso.
Obs: Ok

Caso 9 
⚠️ Código `BASE II SYSTEM` — columna *Definition*
Antes: An electronic batch transmission system primarily used for the exchange of
Visa interchange transaction data and for settlement of the value of those
transactions between acquirers and issuers. This system is also used by
centers to retrieve records from the Advice File and by Visa to settle various
fees with clients.
Ahora: An international electronic batch transmission system primarily used for
the exchange of Visa interchange transaction data and for settlement of
the value of those transactions between acquirers and issuers. Processing
centers use this system to retrieve records from the Advice File. Visa uses the
system to settle fees with clients.
Razón: El texto describe lo mismo pero con una redacción más clara y sin repeticiones
Obs: Ok

Caso 10 
Código `CENTRAL PROCESSING DATE (CPD)` — columna *Definition*
Antes: The date (based on GMT) when the ITF or report in question was generated
at a VIC.
Ahora: The date (based on GMT) on which a client enters Interchange data to, and
the data is accepted by, a VisaNet Interchange Center (VIC).
Razón: El significado de la fecha de generación de los datos cambia de 'cuando se generó el ITF o reporte en un VIC' a 'cuando el cliente ingresa datos al VIC y son aceptados'
Obs: Ok

Caso 11
Código `DESTINATION IDENTIFIER` — columna *Definition*
Antes: See acquiring identifier and/or issuing identifier.
Ahora: An Identifier to which a BASE II transaction message is sent.
Razón: El significado del código cambió de referirse a identificadores de adquisición/emitidos a un identificador de destino específico para transacciones BASE II.
Obs: Ok

Caso 12
Código `ISSUER CENTER` — columna *Definition*
Antes: A BASE II processing center acting in support of one or more issuers. The
processing center processes completed account holder transactions (local
and interchange) for account holder account posting and billing. For
completed interchange transactions, the center is also responsible for
receiving and processing incoming transactions for the account holders of
the issuer or issuers.
Ahora: A BASE II processing center acting in support of one or more issuers.
The processing center processes completed cardholder transactions (local
and interchange) for cardholder account posting and billing. For completed
interchange transactions, the center is also responsible for receiving and
processing incoming transactions for the cardholders of the issuer or issuers.
Razón: El cambio modifica el término 'account holder' por 'cardholder' y 'account posting' por 'cardholder account posting', lo que altera el significado técnico del servicio.
Obs: Ok

Caso 13
Código `ISSUING IDENTIFIER` — columna *Definition*
Antes: A numeric value used to define issuing processing. Multiple Issuing BINs can
be linked to the same Issuing Identifier in Visa's systems.
Ahora: A numeric value used to define issuing processing. It is not governed by ISO
and does not have to start with a four (4). Multiple issuing BINs can be linked
to the same issuing identifier within Visa systems, which can allow mirroring
of processing or routing configurations.
Razón: El texto nuevo especifica que el Issuing Identifier no está gobernado por ISO y no debe comenzar con un 4, lo que modifica su definición comercial.
Obs: Ok 

Caso 14 
Código `PLUS IDENTIFIER FILE` — columna *Definition*
Antes: A file containing Plus table update records that is created through incoming
Edit Package processing for all clients subscribing to the Plus ATM system.
The Plus Table contains identifier numbers of Plus card issuers.
Ahora: A file containing Plus table update records that is created through incoming
Edit Package processing for all clients subscribing to the Plus ATM system.
The Plus Table contains numbers of Plus card issuers.
Razón: El cambio en 'identifier numbers' a 'numbers' altera el significado técnico del código, indicando que el valor de negocio cambió de identificadores a números simples.
Obs: Ok

Caso 15 
⚠️ Código `SOURCE IDENTIFIER` — columna *Definition*
Antes: See acquiring identifier and/or issuing identifier.
Ahora: The Identifier from which a BASE II transaction message is sent.
Razón: El texto describe lo mismo pero con una redacción más clara y específica, sin cambios en el significado.
Obs: OkOk

Caso 16
⚠️ Código `TRANSACTION` — columna *Definition*
Antes: BASE II transaction. The record or records that make up a single financial,
administrative, or text message, as required for transmission between a
processing center and a VIC. BASE II transactions are identified by transaction
codes.
Cardholder transaction. The use of a payment credential to make a payment
or otherwise exhange value between a cardholder (or an issuer) and a
merchant (or an acquirer).
Ahora: BASE II transaction. The record or records that make up a single financial,
administrative, or text message, as required for transmission between a
processing center and a VIC. BASE II transactions are identified by transaction
codes.
Cardholder transaction. The use of a card by a customer (normally assumed
to be the cardholder) to purchase goods or services from a merchant or
secure cash from an ATM or financial institution.
Razón: El texto describe el mismo concepto de transacción del titular de tarjeta, pero con una redacción diferente que especifica el uso de la tarjeta por un cliente para comprar bienes o servicios, en lugar de 'exhange value entre un cardholder y un merchant'.
Obs: Ok

Caso 17
POS Environment Codes (1)
⚠️ Código `R` — columna *Usage Used to indicate that the field is not populated.*
Antes: Use to identify multiple transactions that:
l
l
Examples of a recurring transaction include
periodic membership fees, subscriptions, etc.
Occur at predetermined intervals that do not
exceed 1 year between transactions
Represent an agreement between a
cardholder and a merchant to purchase
goods or services over a period of time.
Ahora: Use to identify multiple transactions that:
●Occur at predetermined intervals that do not
●Represent an agreement between a
Examples of a recurring transaction include
periodic membership fees, subscriptions, etc.
exceed 1 year between transactions
cardholder and a merchant to purchase
goods or services over a period of time.
Razón: El texto se reorganizó para mejorar la legibilidad, manteniendo el mismo significado y contenido.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.

Caso 18
Payment Mode Codes (1)
⚠️ Código `61` — columna *Definition*
Antes: Twice Payment or Installment Payment with Number of Installment Payments
l
l
Twice Payment: number of installment payments = 0 or 2. Settlement between the acquirer
and issuer is deferred for Twice Payment.
Installment Payment: number of installment payments is greater than or equal to 3.
Settlement between the acquirer and issuer is not deferred for Installment Payment.
Ahora: Twice Payment or Installment Payment with Number of Installment Payments
●Twice Payment: number of installment payments = 0 or 2. Settlement between the acquirer
●Installment Payment: number of installment payments is greater than or equal to 3.
and issuer is deferred for Twice Payment.
Settlement between the acquirer and issuer is not deferred for Installment Payment.
Razón: El texto se reorganizó con puntos y espacios diferentes, pero mantiene el mismo significado y contenido.
Obs: Eso que indicas de la razon con mejor formato mas claro, me parece extraño, porque si lo veo igual ambos formatos y mismas palabras.

Caso 19
Product ID Values (3)
Código `G2` — columna *Description*
Antes: Visa Business Check Card
Ahora: Visa Value Business
Razón: El texto descriptivo cambia de 'Visa Business Check Card' a 'Visa Value Business', lo que altera el significado comercial del producto.
Obs: Ok

Caso 20
Código `S1` — columna *Description*
Antes: Visa Purchasing with Fleet
Ahora: Visa Purchasing with Fleet
Visa Fleet (Canada only)
Razón: Se agregó una restricción geográfica específica para el código en el valor nuevo, indicando que solo aplica en Canadá.
Obs: Ok

Caso 21
Código `W1` — columna *Description*
Antes: Visa Direct Payouts A
Ahora: Visa Direct Payouts to Bank Accounts
Razón: El texto describe ahora el pago directo a cuentas bancarias en lugar de un pago directo general, cambiando el significado de negocio.
Obs: Ok

Caso 22
Request for Copy Reason Codes-Copy/Microfilm of Original (TC 52) (2)
Código `33` — columna *Reason*
Antes: l
l
Ahora: ●Legal process or fraud analysis request—U.S. Domestic only
●Fraud analysis request—Non-U.S. Domestic
Razón: El significado del código 33 cambió de ser un texto vacío a especificar dos tipos de solicitudes legales o de análisis de fraude con distinción de territorio.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 23
Código `34` — columna *Reason*
Antes: l
l
Ahora: ●Repeat request for copy—U.S. Domestic only
●Legal process request—Non-U.S. Domestic
Razón: El código 34 ahora incluye dos razones específicas: 'Repeat request for copy—U.S. Domestic only' y 'Legal process request—Non-U.S. Domestic', cambiando su significado de negocio desde un texto vacío a dos condiciones claras.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 24
Código `30` — columna *Chargeback Reason Rules*
Antes: Services Not Provided or Merchandise Not Received
All Regions:
l
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions the minimum amount must be equal to or
greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Services Not Provided or Merchandise Not Received
All Regions:
●ATM is prohibited.
International:
●For T&E transactions the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en Canadá, cambiando el valor de los mínimos de transacciones.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 25
Código `41` — columna *Chargeback Reason Rules*
Antes: Cancelled Recurring Transaction
All Regions:
l
International:
ATM is prohibited.
l
l
U.K. Domestic:
For T&E transaction, the minimum amount must be equal to or
greater than $25.00 USD.
No non-T&E minimum amount.
l
Canada Region:
l
l
Japan Domestic:
l
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Cancelled Recurring Transaction
All Regions:
●ATM is prohibited.
International:
●For T&E transaction, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 USD.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica los límites de monto para transacciones T&E y no T&E en Canadá, especificando valores diferentes que afectan la regla de negocio.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 26
Código `53` — columna *Chargeback Reason Rules*
Antes: Not as Described or Defective Merchandise
All Regions:
l
International:
l
l
U.S. Region:
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
EPS not allowed.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Not as Described or Defective Merchandise
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.S. Region:
than $25.00 USD.
●EPS not allowed.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en el valor mínimo de transacciones en CAD, cambiando el valor anterior de $25.00 USD a $25.00 CAD y $10.00 CAD respectivamente.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 27
Código `57` — columna *Chargeback Reason Rules*
Antes: Fraudulent Multiple Transactions
All Regions:
l
l
l
International:
ATM is prohibited.
Direct Marketing MCCs are prohibited.
MOTO/ECI must be spaces.
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
For T&E transactions, the minimum must be equal to or greater
than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD
T&E and non-T&E, no minimum amount.
Ahora: Fraudulent Multiple Transactions
All Regions:
●ATM is prohibited.
●Direct Marketing MCCs are prohibited.
●MOTO/ECI must be spaces.
International:
●For T&E transactions, the minimum must be equal to or greater than
●No non-T&E minimum amount.
U.K. Domestic:
$25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica los límites de mínimo para transacciones T&E y no T&E en regiones específicas, cambiando el valor anterior de $25.00 USD a $25.00 CAD y $10.00 CAD respectivamente.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 28
Código `60` — columna *Chargeback Reason Rules*
Antes: Illegible Fulfillment
All Regions:
l
International:
l
U.S. Domestic and AP Region:
l
Canada Region:
ATM is prohibited.
No T&E or non-T&E minimum amount.
EPS is not allowed.
l
l
l
Japan Domestic:
l
EPS is not allowed.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Illegible Fulfillment
All Regions:
●ATM is prohibited.
International:
●No T&E or non-T&E minimum amount.
U.S. Domestic and AP Region:
●EPS is not allowed.
Canada Region:
●EPS is not allowed.
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica las reglas de mínimo de monto para transacciones T&E y no T&E en el contexto de Japón, especificando valores numéricos diferentes al valor anterior.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 29
Código `62` — columna *Chargeback Reason Rules*
Antes: Counterfeit Transaction
All Regions:
l
l
International:
l
Canada Region:
l
l
Japan Domestic:
l
Direct Marketing MCCs are prohibited.
MOTO/ECI must be spaces.
No T&E or non-T&E minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Counterfeit Transaction
All Regions:
●Direct Marketing MCCs are prohibited.
●MOTO/ECI must be spaces.
International:
●No T&E or non-T&E minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo reorganiza las reglas de manera que las condiciones para T&E y no T&E se especifican con montos mínimos diferentes, mientras que el valor anterior no distinguía claramente los montos mínimos para cada tipo de transacción.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 30
Código `70` — columna *Chargeback Reason Rules*
Antes: Card Recovery Bulletin or Exception File
All Regions:
l
l
International:
ATM is prohibited.
Validate against the Card Warning Bulletin.
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Card Recovery Bulletin or Exception File
All Regions:
●ATM is prohibited.
●Validate against the Card Warning Bulletin.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 USD.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica los límites de monto para transacciones T&E y no T&E en diferentes regiones, especificando valores distintos para USD y CAD que no estaban claros en la versión anterior.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 31
Código `71` — columna *Chargeback Reason Rules*
Antes: Declined Authorization
All Regions:
l
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Declined Authorization
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas de mínimo monto para transacciones T&E y no T&E en diferentes regiones, alterando el significado de las condiciones comerciales.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 32
Código `72` — columna *Chargeback Reason Rules*
Antes: No Authorization
All Regions:
l
International:
ATM is prohibited.
l
l
U.K. Domestic:
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
l
Canada Region:
l
l
Japan Domestic:
l
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: No Authorization
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 USD.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica los límites de monto para transacciones T&E y no T&E en diferentes regiones, especificando valores diferentes para USD y CAD que no estaban claros en la versión anterior.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 33
Código `73` — columna *Chargeback Reason Rules*
Antes: Expired Card
All Regions:
l
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Expired Card
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en el valor mínimo de transacciones, cambiando el significado de las condiciones aplicables.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual 

Caso 34
Código `74` — columna *Chargeback Reason Rules*
Antes: Late Presentment
International:
l
l
U.S. Domestic:
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
l
l
U.K. Domestic:
Plus ATM cash disbursement and alternate media transactions
are prohibited.
Visa ATM cash disbursement transaction is not allowed.
l
Canada Region:
l
l
Japan Domestic:
l
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Late Presentment
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.S. Domestic:
than $25.00 USD.
●Plus ATM cash disbursement and alternate media transactions are
●Visa ATM cash disbursement transaction is not allowed.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
prohibited.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El cambio modifica la estructura de las reglas de presentación tardía para T&E y no T&E en diferentes regiones, especificando montos diferentes para CAD y USD.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual 

Caso 35
Código `75` — columna *Chargeback Reason Rules*
Antes: Transaction Not Recognized
All Regions:
l
l
International:
l
l
U.S. Region:
l
l
l
U.K. Domestic
l
Canada Region:
l
l
l
Japan Domestic:
l
ATM is prohibited.
Cannot be a Secure Electronic Commerce transaction.
No T&E minimum amount.
No non-T&E minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
EPS not allowed.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
Not valid for EPS/NSR Transactions
T&E and non-T&E, no minimum amount.
Ahora: Transaction Not Recognized
All Regions:
●ATM is prohibited.
●Cannot be a Secure Electronic Commerce transaction.
International:
●No T&E minimum amount.
●No non-T&E minimum amount.
U.S. Region:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
●EPS not allowed.
U.K. Domestic
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
●Not valid for EPS/NSR Transactions
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica las reglas de mínimo monto para transacciones T&E y no T&E en regiones específicas, alterando condiciones de negocio.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual 

Caso 36
Código `76` — columna *Chargeback Reason Rules*
Antes: Incorrect Currency or Transaction Code or Domestic
Transaction Processing Violation
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Incorrect Currency or Transaction Code or Domestic Transaction
Processing Violation
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas de mínimo monto para transacciones T&E y no T&E en diferentes regiones, alterando el significado de las condiciones comerciales.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual 

Caso 37
Código `77` — columna *Chargeback Reason Rules*
Antes: Non-Matching Account Number
All Regions:
l
International:
l
l
U.K. Domestic:
l
Canada Region:
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
l
l
Japan Domestic:
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
l
T&E and non-T&E, no minimum amount.
Ahora: Non-Matching Account Number
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 USD.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica los límites de monto para transacciones T&E y no T&E en diferentes regiones, especificando valores distintos para USD y CAD que no estaban claros en la versión anterior.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual 

Caso 38
Código `78` — columna *Chargeback Reason Rules*
Antes: Service Code Violation
All Regions:
l
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Service Code Violation
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo reorganiza las reglas de mínimo de monto para transacciones T&E y no T&E, alterando el significado de los valores mínimos en USD y CAD.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual  

Caso 39
Código `80` — columna *Chargeback Reason Rules*
Antes: Incorrect Transaction Amount or Account Number
All Regions except U.S. Region:
l
International:
ATM is prohibited.
l
l
U.K. Domestic:
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
l
Canada Region:
l
l
l
Japan Domestic:
l
T&E and non-T&E, no minimum amount.
EPS is not allowed.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Incorrect Transaction Amount or Account Number
All Regions except U.S. Region:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●EPS is not allowed.
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 USD.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica las reglas de mínimo monto para transacciones T&E y no T&E en diferentes regiones, especificando valores diferentes en CAD y USD que no estaban claros en la versión anterior.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 40
Código `81` — columna *Chargeback Reason Rules*
Antes: Fraud - Card-Present Environment
All Regions:
l
l
International:
l
l
l
U.S. Region:
l
l
AP Region:
l
U.K. Domestic:
l
Canada Region:
l
l
l
Japan Domestic:
l
MOTO/ECI must be spaces.
Direct Marketing MCCs are prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
ATM is prohibited
For Automated Fuel Dispenser transactions, the minimum
amount must be equal to or greater than $10.00 USD.
ATM is prohibited
EPS not allowed.
T&E and non-T&E, no minimum amount.
EPS is not allowed.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Fraud - Card-Present Environment
All Regions:
●MOTO/ECI must be spaces.
●Direct Marketing MCCs are prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
●ATM is prohibited
U.S. Region:
than $25.00 USD.
●For Automated Fuel Dispenser transactions, the minimum amount must be
●ATM is prohibited
AP Region:
equal to or greater than $10.00 USD.
●EPS not allowed.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●EPS is not allowed.
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en CAD, cambiando el valor mínimo de transacción desde $25.00 USD a $25.00 CAD y $10.00 CAD respectivamente.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 41
⚠️ Código `82` — columna *Chargeback Reason Rules*
Antes: Duplicate Processing
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Duplicate Processing
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto se reorganizó para mejorar la legibilidad, manteniendo el mismo significado y reglas de negocio.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 42
Código `83` — columna *Chargeback Reason Rules*
Antes: Fraud - Card-Absent Environment
All Regions:
l
l
International:
l
l
U.K. Domestic:
l
Canada Region:
ATM is prohibited.
Restricted for use by Secure Electronic Commerce transactions,
except by U.S. region.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
l
l
Japan Domestic:
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
l
T&E and non-T&E, no minimum amount.
Ahora: Fraud - Card-Absent Environment
All Regions:
●ATM is prohibited.
●Restricted for use by Secure Electronic Commerce transactions, except by
International:
U.S. region.
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 USD.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en el Canada Region, especificando que el mínimo para T&E es $25.00 USD y para no T&E es $10.00 CAD, mientras que el texto antiguo no tenía claridad en el monto para no T&E en Canada.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 43
Código `85` — columna *Chargeback Reason Rules*
Antes: Credit Not Processed
All Regions:
l
International:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Credit Not Processed
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.K. Domestic:
than $25.00 USD.
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en el contexto de transacciones domésticas en Canadá, alterando la interpretación del mínimo requerido.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 44
Código `86` — columna *Chargeback Reason Rules*
Antes: Paid by Other Means
All Regions:
l
International:
l
l
U.S. Region:
l
AP Region:
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
ATM is prohibited.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 USD.
No non-T&E minimum amount.
EPS not allowed.
EPS not allowed.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Paid by Other Means
All Regions:
●ATM is prohibited.
International:
●For T&E transactions, the minimum amount must be equal to or greater
●No non-T&E minimum amount.
U.S. Region:
than $25.00 USD.
●EPS not allowed.
AP Region:
●EPS not allowed.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica el orden de las reglas para T&E y no T&E en el valor mínimo de transacciones en CAD, cambiando el monto mínimo de $25.00 USD a $25.00 CAD y $10.00 CAD respectivamente.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 45
Código `90` — columna *Chargeback Reason Rules*
Antes: Non-Receipt of Cash or Load Transaction Value at ATM or
Load Device
International:
l
U.S. Region:
l
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
T&E and non-T&E, no minimum amount.
T&E and Non-T&E not allowed.
Valid for ATM only.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Non-Receipt of Cash or Load Transaction Value at ATM or Load Device
International:
●T&E and non-T&E, no minimum amount.
U.S. Region:
●T&E and Non-T&E not allowed.
●Valid for ATM only.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
than $25.00 CAD.
greater than $10.00 CAD.
●T&E and non-T&E, no minimum amount.
Razón: El texto nuevo modifica las reglas de mínimo monto para transacciones T&E y no T&E en Canadá, especificando valores diferentes al valor anterior.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 46
⚠️ Código `93` — columna *Chargeback Reason Rules*
Antes: Merchant Fraud Performance
All Regions:
l
International:
ATM is prohibited.
l
U.K. Domestic:
l
Canada Region:
l
l
Japan Domestic:
l
T&E and non-T&E, no minimum amount.
T&E and non-T&E, no minimum amount.
For T&E transactions, the minimum amount must be equal to
or greater than $25.00 CAD.
For non-T&E transactions, the minimum amount must be equal
to or greater than $10.00 CAD.
T&E and non-T&E, no minimum amount.
Ahora: Merchant Fraud Performance
All Regions:
●ATM is prohibited.
International:
●T&E and non-T&E, no minimum amount.
U.K. Domestic:
●T&E and non-T&E, no minimum amount.
Canada Region:
●For T&E transactions, the minimum amount must be equal to or greater
●For non-T&E transactions, the minimum amount must be equal to or
Japan Domestic:
●T&E and non-T&E, no minimum amount.
than $25.00 CAD.
greater than $10.00 CAD.
Razón: El texto se reescribe con formato de listas y puntos en lugar de líneas en blanco, pero mantiene el mismo significado y reglas de comercio.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 47
⚠️ Código `01` — columna *Error Condition*
Antes: The Hash Total is invalid. If data is from a local tape, a problem occurred in the Edit
Package. The VAP checks the Hash Total while loading the file, so if the data is from one of
these devices or is inter-VIC, an invalid Hash Total indicates one of these issues
l
l
l
Noise on the communication line has modified the data.
The sending VAP or VIC is not using the same Data Structure Table that the receiving
VIC is using, which caused the receiving VIC to incorrectly expand the transaction.
The file was modified after the Edit Package was executed.
Ahora: The Hash Total is invalid. If data is from a local tape, a problem occurred in the Edit
Package. The VAP checks the Hash Total while loading the file, so if the data is from one of
these devices or is inter-VIC, an invalid Hash Total indicates one of these issues
●Noise on the communication line has modified the data.
●The sending VAP or VIC is not using the same Data Structure Table that the receiving
●The file was modified after the Edit Package was executed.
VIC is using, which caused the receiving VIC to incorrectly expand the transaction.
Razón: El texto se reorganizó para usar bullets en lugar de líneas separadas, manteniendo el mismo significado.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual

Caso 48
⚠️ Código `HZ` — columna *Error Condition*
Antes: The recalculation of the validation code at the VIC showed that one of the fields listed
below did not match the value in the authorization message. Please resubmit.
l
l
l
l
l
l
l
l
l
l
l
l
CPS/ATM:
Account Number
Authorized Amount
Authorization Characteristics Indicator
Authorization Code
Authorization Currency Code
Authorization Response Code
Cashback
Market-Specific Authorization Indicator
Merchant Category Code
POS Entry Mode
Transaction Identifier
Product ID
l
l
l
l
l
l
l
l
l
Account Number
Authorization Characteristics Indicator
Transaction Identifier
Authorized Amount
Authorization Currency Code
Merchant Country Code
ATM Account Selection
Acquiring Identifier
Surcharge Amount
Ahora: The recalculation of the validation code at the VIC showed that one of the fields listed
below did not match the value in the authorization message. Please resubmit.
Razón: El texto se simplificó eliminando los detalles específicos de los campos que antes se listaban, manteniendo el mismo mensaje sin cambios de significado.
Obs: Es por el formato de viñetas que menciono en otros casos de arriba, porque aca por culpa del formato/diseño de viñetas parece que hay una diferencia. Sin embarog ambos muestran la informacion igual
