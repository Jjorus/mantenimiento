import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

// Core
import 'core/api/dio_client.dart';
import 'core/services/storage_service.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';

// Data
import 'data/datasources/auth_remote_ds.dart';
import 'data/repositories/auth_repository.dart';

// Logic
import 'logic/auth_cubit/auth_cubit.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  final storageService = StorageService();
  final dioClient = DioClient(storageService);
  final authRemoteDs = AuthRemoteDataSource(dioClient);
  final authRepository = AuthRepository(
    remoteDs: authRemoteDs,
    storage: storageService,
  );

  runApp(MyApp(authRepository: authRepository));
}

class MyApp extends StatelessWidget {
  final AuthRepository authRepository;

  const MyApp({super.key, required this.authRepository});

  @override
  Widget build(BuildContext context) {
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider<AuthRepository>.value(value: authRepository),
      ],
      child: MultiBlocProvider(
        providers: [
          BlocProvider<AuthCubit>(
            create: (context) => AuthCubit(
              context.read<AuthRepository>(),
            ),
          ),
        ],
        // Usamos Builder para tener contexto con los Providers ya disponibles
        child: Builder(
          builder: (context) {
            // Inyectamos el AuthCubit en el router para redirecciones
            final router = AppRouter.router(context.read<AuthCubit>());

            return MaterialApp.router(
              title: 'Mantenimiento App',
              debugShowCheckedModeBanner: false,
              theme: AppTheme.lightTheme,
              darkTheme: AppTheme.darkTheme,
              themeMode: ThemeMode.system,
              
              // Configuración de GoRouter
              routerConfig: router,
            );
          },
        ),
      ),
    );
  }
}