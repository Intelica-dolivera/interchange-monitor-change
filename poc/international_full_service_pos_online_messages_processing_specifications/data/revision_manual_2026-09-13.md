caso 1:
Full Service Processing Summary > Full Service Participation Requirements > Issuer Options (1)
Párrafo cambiado
Antes: Field 55 may contain tags that the receiving issuer or acquirer does not recognize, or does not expect. The receiver must ignore such tags and continue parsing the next tag in field 55. Country-to-Country Transactions V.I.P. maintains a Country-to-Country table that allows full service issuers to control purchase and cash transactions between countries using country-specific and issuer-specified parameters. The table is predominately used, however, to list countries in which card usage is restricted or prohibited, for instance, between Country A acquirers and Country B issuers. The country-to-country table is updated only by Visa.
Ahora: Field 55 may contain tags that the receiving issuer or acquirer does not recognize, or does not expect. The receiver must ignore such tags and continue parsing the next tag in field 55. Country-to-Country Transactions V.I.P. maintains a Country-to-Country table that allows full service issuers to control purchase and cash transactions between countries using country-specific and issuer-specified parameters. The table is predominately used, however, to list countries in which card usage is restricted or prohibited, for instance, between Country A acquirers and Country B issuers. The country-to-country table is updated only by Visa. These parameters are involved in establishing a V.I.P. country-to-country block:
Razón: La nueva edición añade información adicional sobre los parámetros involucrados en la creación de un bloque de país a país en V.I.P., lo que modifica la regla de negocio al especificar un requisito adicional para el procesamiento.
obs: Me parece extraño que lo indiques como diferencia ya que ambos textos son iguales en esa seccion.
en la anterior es:
Field 55 may contain tags that the receiving issuer or acquirer does not recognize, or does not expect. The receiver must ignore such tags and continue parsing the next tag in field 55.
Country-to-Country Transactions
V.I.P. maintains a Country-to-Country table that allows full service issuers to control purchase and cash transactions between countries using country-specific and issuer-specified parameters. The table is predominately used, however, to list countries in which card usage is restricted or prohibited, for instance, between Country A acquirers and Country B issuers. The country-to-country table is updated only by Visa.
These parameters are involved in establishing a V.I.P. country-to-country block:
l
Issuer and acquirer country codes
l
Card type, for instance, Visa card
l
Card program, for instance, Classic or Platinum
l
Whether to block purchase transactions, cash transactions, or both
l
Whether cards are valid in all countries, valid only in the issuing country, valid in countries identified in the table for the issuing identifier, or invalid in countries identified in the table for the issuing identifier.
When checking the table, V.I.P. determines if a country is embargoed and if it is, whether the embargo includes cash transactions, POS transactions, or both. When a match is found, V.I.P. assigns response code 62 (restricted card) and STIP declines the transaction.

En la nueva es:
Field 55 may contain tags that the receiving issuer or acquirer does not recognize, or does not expect. The receiver must ignore such tags and continue parsing the next tag in field 55.
Country-to-Country Transactions
V.I.P. maintains a Country-to-Country table that allows full service issuers to control purchase and cash transactions between countries using country-specific and issuer-specified parameters. The table is predominately used, however, to list countries in which card usage is restricted or prohibited, for instance, between Country A acquirers and Country B issuers. The country-to-country table is updated only by Visa.
[aqui sucede un cambio de pagina]
The following parameters are involved in establishing a V.I.P. country-to-country block:
l
Issuer and acquirer country codes
l
Card type, for instance, Visa card
l
Card program, for instance, Classic or Platinum
l
Whether to block purchase transactions, cash transactions, or both
l
Whether cards are valid in all countries, valid only in the issuing country, valid in countries identified in the table for the issuing identifier, or invalid in countries identified in the table for the issuing identifier.
When checking the table, V.I.P. determines if a country is embargoed and if it is, whether the embargo includes cash transactions, POS transactions, or both. When a match is found, V.I.P. assigns response code 62 (restricted card) and STIP declines the transaction.

Puede ser que sea por el cambio de pagina que hay entre cada sección.

Caso 2:
Stand-In Processing (STIP) > Assigning a Response Code > Converting Over-Limit Codes in Acquirer Responses (1)
Párrafo cambiado
Antes: Converting Approval, Forward-or-Approve, Decline, or Incorrect CVV or iCVV Response Codes
Ahora: Converting Approval, Forward-or-Approve, Decline, or Incorrect CVV or iCVV Response Code XA
Razón: La edición nueva especifica un código específico (XA) en lugar de listar tipos de códigos, lo que indica un cambio en la regla de negocio sobre qué código se convierte.
Obs: Ok

Transaction Sets > Visa POS Transaction Sets (1)
Párrafo cambiado
Antes: 1Includes purchase with cashback, purchase with address verification (Visa POS only), quasi-cash, and key- entered purchase.
Ahora: Includes purchase with cashback, purchase with address verifi­ cation (Visa POS only), quasi-cash, and key- entered purchase. Adjustment
Razón: Se añadió la palabra 'Adjustment' al final, lo que sugiere un nuevo tipo de transacción o ajuste que antes no estaba incluido en la definición.
Obs: Ok