Caso 1:
Description
Antes: An electronic batch transmission system primarily used for the exchange of Visa interchange transaction data and for settlement of the value of those transactions between acquirers and issuers. This system is also used by centers to retrieve records from the Advice File and by Visa to settle various fees with clients.
Ahora: An international electronic batch transmission system primarily used for the exchange of Visa interchange transaction data and for settlement of the value of those transactions between acquirers and issuers. Processing centers use this system to retrieve records from the Advice File. Visa uses the system to settle fees with clients.
Razón: El texto nuevo especifica que es un sistema internacional y modifica el uso de los centros de procesamiento y Visa para la retención de registros y cobros, lo que cambia el significado de negocio.
Obs: Ok

Caso 2:
`V0173` — CASHBACK AMOUNT MUST BE LESS THAN OR EQUAL TO SOURCE AMOUNT (3)
Título
Antes: CASHBACK AMOUNT MUST BE LESS THAN SOURCE AMOUNT
Ahora: CASHBACK AMOUNT MUST BE LESS THAN OR EQUAL TO SOURCE AMOUNT
Razón: El mensaje original indicaba que la cantidad de cashback debe ser menor que la cantidad fuente, mientras que la nueva versión establece que debe ser menor o igual, lo que cambia la condición de validación.
Obs: Ok

Caso 3:
Description
Antes: The cashback amount must be numeric and must be less than the Source Amount for Canada domestic transactions.
Ahora: The cashback amount must be numeric and must be less than or equal to the Source Amount for Canada domestic transactions.
Razón: El cambio modifica la condición de validación de que el cashback debe ser menor o igual que el Source Amount en lugar de menor, lo que altera el rango de valores permitidos.
Obs: Ok

Caso 4:
Transaction Types
Antes: Sales Draft – All
Ahora: Sales Draft – All | Account Funding – All
Razón: La lista de Transaction Types se amplio para incluir 'Account Funding – All', lo que modifica la condicion de validacion para el cashback.
Obs: Ok

Caso 5:
`V0188` — CASHBACK AMOUNT MUST BE LESS THAN OR EQUAL TO SOURCE AMOUNT (2)
Título
Antes: CASHBACK AMOUNT MUST BE LESS THAN SOURCE AMOUNT
Ahora: CASHBACK AMOUNT MUST BE LESS THAN OR EQUAL TO SOURCE AMOUNT
Razón: El mensaje original indicaba que la cantidad de cashback
Obs: Ok

Caso 6:
Description
Antes: The cashback amount must be numeric, must not be less than zero, and must be less than the Source Amount for U.S. domestic transactions.
Ahora: The cashback amount must be numeric, must not be less than zero, and must be less than or equal to the Source Amount for U.S. domestic transactions.
Razón: El cambio modifica la condición de validación para que el cashback amount sea menor o igual que el Source Amount, en lugar de menor, lo que altera la lógica de negocio.
Obs: Ok

Caso 7:
`V1098` — CASHBACK MUST BE LESS THAN OR EQUAL TO SOURCE AMOUNT (3)
Título
Antes: CASHBACK MUST BE LESS THAN SOURCE AMOUNT FOR PURCHASE AND CREDIT VOUCHER TRANSACTIONS
Ahora: CASHBACK MUST BE LESS THAN OR EQUAL TO SOURCE AMOUNT
Razón: El mensaje original especificaba que el cashback debe ser menor que el monto fuente, mientras que el nuevo mensaje indica que debe ser menor o igual, lo que cambia la condición de validación.
Obs: Ok

Caso 8:
Description
Antes: For AP, CEMEA, and EU transactions, the cashback amount must be less than the source amount. Europe regional transactions submitted with issuer, acquirer, or merchant from UK or Ireland are excluded from this edit. South Africa NNSS transactions are excluded from this edit.
Ahora: For AP, Canada, CEMEA, EU, and cross-border transactions, the cashback amount must be less than or equal to the source amount.
Razón: El cambio modifica la condición de validación al incluir transacciones cruzadas y especificar que el cashback debe ser menor o igual que el source amount, en lugar de menor, además de excluir transacciones específicas en la versión antigua.
Obs: Ok

Caso 9:
Action
Antes: Verify that the Cashback amount is less than the Source amount.
Ahora: Verify that the Cashback amount is less than or equal to the Source amount.
Razón: El cambio modifica la condición de validación de que el Cashback debe ser menor o igual que el Source amount, en lugar de menor, lo que altera la lógica de negocio.
Obs: Ok

