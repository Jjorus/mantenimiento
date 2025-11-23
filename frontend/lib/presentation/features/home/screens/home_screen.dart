import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/auth_cubit/auth_cubit.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.read<AuthCubit>().state.user;
    
    return Scaffold(
      appBar: AppBar(title: const Text("Inicio")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.home_work, size: 80, color: Theme.of(context).primaryColor),
            const SizedBox(height: 20),
            Text(
              "Bienvenido, ${user?.username}", 
              style: Theme.of(context).textTheme.headlineSmall
            ),
            const SizedBox(height: 8),
            Chip(
              label: Text("Rol: ${user?.role}"), 
              backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest
            ),
          ],
        ),
      ),
    );
  }
}