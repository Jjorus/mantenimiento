import 'package:flutter/material.dart';
import 'core/api/dio_client.dart';
import 'core/services/storage_service.dart';
import 'core/theme/app_theme.dart';

void main() {
  // Asegura que el motor gráfico de Flutter esté listo antes de lógica
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Inyección de Dependencias (Manual)
  // Inicializamos los servicios que usará toda la app
  final storageService = StorageService();
  final dioClient = DioClient(storageService);

  // 2. Arrancamos la App pasando las dependencias
  runApp(MyApp(dioClient: dioClient));
}

class MyApp extends StatelessWidget {
  final DioClient dioClient;

  const MyApp({super.key, required this.dioClient});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mantenimiento App',
      
      // Quitamos la etiqueta "DEBUG" de la esquina
      debugShowCheckedModeBanner: false,

      // Configuración de Temas (Clean Lab vs Industrial Dark)
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      
      // Usa el modo del sistema (si Windows está en oscuro, la app también)
      themeMode: ThemeMode.system,

      // Pantalla temporal hasta que hagamos el Login (Fase 2)
      home: const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.check_circle, size: 64, color: Colors.green),
              SizedBox(height: 16),
              Text(
                "Fase 1: Infraestructura OK",
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              Text("Listo para implementar Login"),
            ],
          ),
        ),
      ),
    );
  }
}