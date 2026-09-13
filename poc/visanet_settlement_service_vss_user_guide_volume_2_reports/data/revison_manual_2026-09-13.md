Caso 1:
Apéndice D: SMS Reports and Raw Data — Financial Transaction Fee Record – V22261 (1)
Fila **filler** — columna Position
Antes: 62–130
Ahora: 63–130
Razón: El rango de posiciones cambia de 62–130 a 63–130, lo que indica una modificación en la regla de negocio relacionada con los límites de posiciones.
Obs: Ok

Caso 2:
péndice D: SMS Reports and Raw Data — Financial Transaction Fee Record – V23210 (2)
Fila **filler** — columna Attribute
Antes: 82 AN
Ahora: 81 AN
Razón: El código de atributo cambió de 82 a 81, lo que indica una modificación en la regla de negocio relacionada con el cálculo de tarifas.
Obs: Ok

Caso 3:
Fila **filler** — columna Position
Antes: 43–130
Ahora: 44–130
Razón: El rango de posición cambió de 43–130 a 44–130, lo que indica un cambio en la regla de negocio relacionado con los límites de posición.
Obs: Ok

Caso 4:
Apéndice D: SMS Reports and Raw Data — Financial Transaction Record 1.1 – V22201 (1)
Fila **filler** — columna Position
Antes: 79–130
Ahora: 98–130
Razón: El rango de posiciones cambia de 79-130 a 98-130, lo que indica una modificación en la regla de negocio que define el rango válido.
Obs: Ok

Caso 5:
Apéndice D: SMS Reports and Raw Data — Financial Transaction Record 3 – V23202 (1)
Fila **service processing type** — columna Comments
Antes: This field contains a value that identifies the deferred OCT request type. Valid Values are: 00 (Not a deferred OCT) 01 (Originator hold) 02 (Visa deferred OCT hold, default interval) 09 (Cancel pending deferred OCT request) 0Q (Query the status of the deferred OCT) Note: The values of 09 and 0Q are logged only for the originating acquirer.
Ahora: This field contains a value that identifies the deferred OCT request type. Valid Values are: 00 (Not a deferred OCT) 01 (Originator hold) 02 (Visa deferred OCT hold, default interval) 09 (Cancel pending deferred OCT request) 0Q (Query the status of the deferred OCT) 0R (Recycling Payout) Note: The values of 09, 0Q, and 0R are logged only for the originating acquirer.
Razón: Se agregó un nuevo valor válido '0R (Recycling Payout)' a la lista de valores del campo, lo que modifica la regla de negocio.
Obs: Ok

Caso 6:
Apéndice D: SMS Reports and Raw Data — Financial Transaction Record 4 – V23203 (1)
Fila **filler** — columna Position
Antes: 39–130
Ahora: 58–130
Razón: El rango de posiciones cambia de 39-130 a 58-130, lo que indica una modificación en la regla de negocio que define el rango válido.
Obs: Ok

Caso 7:
Apéndice D: SMS Reports and Raw Data — Financial Transaction Record 5 – V22226 (2)
Fila **filler** — columna Attribute
Antes: 6 AN
Ahora: 4 AN
Razón: El valor de la columna 'Attribute' cambia de '6 AN' a '4 AN', lo que indica una modificación en la regla de negocio relacionada con el valor numérico.
Obs: Ok

Caso 8:
Fila **filler** — columna Position
Antes: 125–130
Ahora: 127–130
Razón: El rango de valores cambia de 125–130 a 127–130, lo que indica un cambio en la regla de negocio sobre el rango de transacciones.
Obs: Ok

Caso 9:
Apéndice D: SMS Reports and Raw Data — Financial Transaction Record/mVisa Record – V22228 (1)
Fila **service processing type** — columna Comments
Antes: This field will contain a value that identifies the deferred OCT request type. Valid values are: 00 (Not a deferred OCT) 01 (Originator hold) 02 (Visa deferred OCT hold, default interval) 09 (Cancel pending deferred OCT request) 0Q (Query the status of the deferred OCT) Note: The values of 09 and 0Q are logged only for the originating acquirer.
Ahora: This field will contain a value that identifies the deferred OCT request type. Valid values are: 00 (Not a deferred OCT) 01 (Originator hold) 02 (Visa deferred OCT hold, default interval) 09 (Cancel pending deferred OCT request) 0Q (Query the status of the deferred OCT) 0R (Recycling Payout) Note: The values of 09, 0Q, and 0R are logged only for the originating acquirer.
Razón: Se agregó un nuevo valor válido (0R) en la lista de tipos de solicitudes de OCT deferidas, lo que modifica la regla de negocio.
Obs: Ok

