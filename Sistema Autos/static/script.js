// Acceso a la cámara
const video = document.getElementById('video');
const canvas = document.createElement('canvas');
const escanearBtn = document.getElementById('escanear-btn');
const qrDataInput = document.getElementById('qr_data');
const mensaje = document.getElementById('mensaje');
const nombreTecnicoInput = document.getElementById('nombre_persona');
const ultimoMantenimientoInput = document.getElementById('ultimo_mantenimiento');

// Acceder a la cámara
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(err => {
        console.error("Error al acceder a la cámara: ", err);
    });

escanearBtn.addEventListener('click', () => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL('image/png').replace(/^data:image\/(png|jpg);base64,/, '');

    fetch('/escaneo_qr', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image: imageData })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mensaje.textContent = "QR detectado: " + data.qr_data;
            qrDataInput.value = data.qr_data;
            console.log("QR Data Capturado:", data.qr_data);

            // Nueva funcionalidad: Verificar si el QR ya existe
            fetch('/verificar_qr', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ qr_data: data.qr_data })
            })
            .then(response => response.json())
            .then(qrInfo => {
                if (qrInfo.exists) {
                    nombreTecnicoInput.value = qrInfo.nombre_tecnico;
                    ultimoMantenimientoInput.value = qrInfo.ultimo_mantenimiento;
                    mensaje.textContent += " (Datos existentes cargados)";
                } else {
                    nombreTecnicoInput.value = '';
                    ultimoMantenimientoInput.value = '';
                    mensaje.textContent += " (Nuevo QR, ingrese los datos)";
                }
            })
            .catch(err => {
                console.error('Error al verificar el QR: ', err);
            });
        } else {
            mensaje.textContent = "No se detectó ningún QR.";
        }
    })
    .catch(err => {
        console.error('Error al procesar la imagen: ', err);
    });
});

// Funcionalidad para el checklist
document.addEventListener('DOMContentLoaded', function() {
    const numeroCocheInput = document.getElementById('numero_coche');
    if (numeroCocheInput) {
        numeroCocheInput.addEventListener('change', function() {
            const numeroCoche = this.value;
            if (numeroCoche) {
                fetch(`/get_car_details/${numeroCoche}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            console.log(data.error);
                            return;
                        }
                        document.getElementById('kilometraje').value = data.kilometraje;
                        document.getElementById('estado_llantas').value = data.estado_llantas;
                        document.getElementById('estado_rines').value = data.estado_rines;
                        document.getElementById('detalles_raspones').value = data.detalles_raspones;
                        document.getElementById('estado_faros').value = data.estado_faros;
                        document.getElementById('otros_detalles').value = data.otros_detalles;
                        document.getElementById('lastUpdate').textContent = `Última actualización: ${data.ultima_actualizacion}`;
                    })
                    .catch(error => console.error('Error:', error));
            }
        });
    }
});