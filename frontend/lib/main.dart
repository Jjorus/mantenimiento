import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

// Core
import 'core/api/dio_client.dart';
import 'core/services/storage_service.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';

// Data Sources
import 'data/datasources/auth_remote_ds.dart';
import 'data/datasources/inventory_remote_ds.dart';
import 'data/datasources/movement_remote_ds.dart';
import 'data/datasources/maintenance_remote_ds.dart';
import 'data/datasources/admin_remote_ds.dart'; // NUEVO

// Repositories
import 'data/repositories/auth_repository.dart';
import 'data/repositories/inventory_repository.dart';
import 'data/repositories/movement_repository.dart';
import 'data/repositories/maintenance_repository.dart';
import 'data/repositories/admin_repository.dart'; // NUEVO

// Logic
import 'logic/auth_cubit/auth_cubit.dart';
import 'logic/movement_cubit/movement_cubit.dart';
import 'logic/inventory_cubit/inventory_cubit.dart';
import 'logic/maintenance_cubit/maintenance_cubit.dart';
import 'logic/admin_cubit/admin_cubit.dart'; // NUEVO

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
  final adminRemoteDs = AdminRemoteDataSource(dioClient); // NUEVO

  // 3. Repositorios
  final authRepository = AuthRepository(
    remoteDs: authRemoteDs,
    storage: storageService,
  );
  final inventoryRepository = InventoryRepository(remoteDs: invRemoteDs);
  final movementRepository = MovementRepository(remoteDs: movRemoteDs);
  final maintenanceRepository = MaintenanceRepository(remoteDs: maintRemoteDs);
  final adminRepository = AdminRepository(remoteDs: adminRemoteDs); // NUEVO

  runApp(MyApp(
    authRepository: authRepository,
    inventoryRepository: inventoryRepository,
    movementRepository: movementRepository,
    maintenanceRepository: maintenanceRepository,
    adminRepository: adminRepository, // NUEVO
  ));
}

class MyApp extends StatelessWidget {
  final AuthRepository authRepository;
  final InventoryRepository inventoryRepository;
  final MovementRepository movementRepository;
  final MaintenanceRepository maintenanceRepository;
  final AdminRepository adminRepository; // NUEVO

  const MyApp({
    super.key, 
    required this.authRepository,
    required this.inventoryRepository,
    required this.movementRepository,
    required this.maintenanceRepository,
    required this.adminRepository, // NUEVO
  });

  @override
  Widget build(BuildContext context) {
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider.value(value: authRepository),
        RepositoryProvider.value(value: inventoryRepository),
        RepositoryProvider.value(value: movementRepository),
        RepositoryProvider.value(value: maintenanceRepository),
        RepositoryProvider.value(value: adminRepository), // NUEVO
      ],
      child: MultiBlocProvider(
        providers: [
          // Auth Global
          BlocProvider<AuthCubit>(
            create: (context) => AuthCubit(context.read<AuthRepository>()),
          ),
          // Movimientos Global
          BlocProvider<MovementCubit>(
            create: (context) => MovementCubit(context.read<MovementRepository>()),
          ),
          // Inventario Global
          BlocProvider<InventoryCubit>(
            create: (context) => InventoryCubit(
              context.read<InventoryRepository>(), 
            ),
          ),
          // Mantenimiento Global
          BlocProvider<MaintenanceCubit>(
            create: (context) => MaintenanceCubit(context.read<MaintenanceRepository>()),
          ),
          // Admin Global (Para gestión de usuarios y paneles admin)
          BlocProvider<AdminCubit>(
            create: (context) => AdminCubit(context.read<AdminRepository>()),
          ),
        ],
        child: Builder(
          builder: (context) {
            // Le pasamos el AuthCubit al router para la redirección (login/logout)
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
