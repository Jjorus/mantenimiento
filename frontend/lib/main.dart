import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

// Core
import 'core/api/dio_client.dart';
import 'core/services/storage_service.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';

// Data Sources
import 'data/datasources/auth_remote_ds.dart';
import 'data/datasources/inventory_remote_ds.dart'; // NUEVO
import 'data/datasources/movement_remote_ds.dart';  // NUEVO
import 'data/datasources/maintenance_remote_ds.dart';

// Repositories
import 'data/repositories/auth_repository.dart';
import 'data/repositories/inventory_repository.dart'; // NUEVO
import 'data/repositories/movement_repository.dart';  // NUEVO
import 'data/repositories/maintenance_repository.dart';

// Logic
import 'logic/auth_cubit/auth_cubit.dart';
import 'logic/movement_cubit/movement_cubit.dart';    // NUEVO
import 'logic/inventory_cubit/inventory_cubit.dart';
import 'logic/maintenance_cubit/maintenance_cubit.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Servicios Base
  final storageService = StorageService();
  final dioClient = DioClient(storageService);

  // 2. Data Sources
  final authRemoteDs = AuthRemoteDataSource(dioClient);
  final invRemoteDs = InventoryRemoteDataSource(dioClient);
  final movRemoteDs = MovementRemoteDataSource(dioClient);
  final maintRemoteDs = MaintenanceRemoteDataSource(dioClient);

  // 3. Repositorios
  final authRepository = AuthRepository(
    remoteDs: authRemoteDs,
    storage: storageService,
  );
  final inventoryRepository = InventoryRepository(remoteDs: invRemoteDs);
  final movementRepository = MovementRepository(remoteDs: movRemoteDs);
  final maintenanceRepository = MaintenanceRepository(remoteDs: maintRemoteDs);

  runApp(MyApp(
    authRepository: authRepository,
    inventoryRepository: inventoryRepository,
    movementRepository: movementRepository,
    maintenanceRepository: maintenanceRepository,
  ));
}

class MyApp extends StatelessWidget {
  final AuthRepository authRepository;
  final InventoryRepository inventoryRepository;
  final MovementRepository movementRepository;
  final MaintenanceRepository maintenanceRepository;

  const MyApp({
    super.key, 
    required this.authRepository,
    required this.inventoryRepository,
    required this.movementRepository,
    required this.maintenanceRepository,
  });

  @override
  Widget build(BuildContext context) {
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider.value(value: authRepository),
        RepositoryProvider.value(value: inventoryRepository),
        RepositoryProvider.value(value: movementRepository),
        RepositoryProvider.value(value: maintenanceRepository),
      ],
      child: MultiBlocProvider(
        providers: [
          BlocProvider<AuthCubit>(
            create: (context) => AuthCubit(context.read<AuthRepository>()),
          ),
          //Cubit global para movimientos (accesible desde cualquier ruta)
          BlocProvider<MovementCubit>(
            create: (context) => MovementCubit(context.read<MovementRepository>()),
          ),
          //logica de inventario y gestion de equipos
          BlocProvider<InventoryCubit>(
            create: (context) => InventoryCubit(
              context.read<InventoryRepository>(), 
            ),
          ),
          //logica de mantenimiento e incidencias
          BlocProvider<MaintenanceCubit>(
            create: (context) => MaintenanceCubit(context.read<MaintenanceRepository>()),
          ),
        ],
        child: Builder(
          builder: (context) {
            final router = AppRouter.router(context.read<AuthCubit>());

            return MaterialApp.router(
              title: 'Mantenimiento App',
              debugShowCheckedModeBanner: false,
              theme: AppTheme.lightTheme,
              darkTheme: AppTheme.darkTheme,
              themeMode: ThemeMode.system,
              routerConfig: router,
            );
          },
        ),
      ),
    );
  }
}