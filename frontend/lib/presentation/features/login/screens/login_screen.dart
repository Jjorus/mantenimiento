import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../logic/auth_cubit/auth_cubit.dart';
import '../../../../logic/auth_cubit/auth_state.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

// AÑADIDO: WidgetsBindingObserver para detectar si perdemos/ganamos foco de ventana
class _LoginScreenState extends State<LoginScreen> with WidgetsBindingObserver {
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  
  final FocusNode _userFocusNode = FocusNode();
  
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // 1. Nos registramos para escuchar cambios de estado de la ventana
    WidgetsBinding.instance.addObserver(this);

    // 2. Aumentamos el retraso a 800ms para esquivar el overlay de NVIDIA/Windows
    Future.delayed(const Duration(milliseconds: 800), () {
      if (mounted) {
        _requestUserFocus();
      }
    });
  }

  @override
  void dispose() {
    // 3. Limpieza del observador
    WidgetsBinding.instance.removeObserver(this);
    _userController.dispose();
    _passController.dispose();
    _userFocusNode.dispose();
    super.dispose();
  }

  // 4. Detectar cuando la app vuelve a primer plano (Resumed)
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // Si el overlay de NVIDIA nos robó el foco y se fue, 
      // al volver a estar activa la ventana, recuperamos el cursor.
      // Solo si no estamos cargando y el campo está vacío.
      if (!_isLoading && _userController.text.isEmpty) {
        _requestUserFocus();
      }
    }
  }

  void _requestUserFocus() {
    FocusScope.of(context).requestFocus(_userFocusNode);
  }

  void _onLoginPressed() async {
    final form = _formKey.currentState;
    if (form == null || !form.validate()) return;

    setState(() => _isLoading = true);

    await context.read<AuthCubit>().login(
      _userController.text.trim(),
      _passController.text.trim(),
    );

    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dynamicTextColor = Theme.of(context).colorScheme.onSurface;

    return BlocConsumer<AuthCubit, AuthState>(
      listener: (context, state) {
        if (state.status == AuthStatus.unauthenticated && state.errorMessage != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(state.errorMessage!),
              backgroundColor: Colors.red.shade700,
              behavior: SnackBarBehavior.floating,
            ),
          );
          _requestUserFocus();
        }
      },
      builder: (context, state) {
        final isCheckingSession = state.status == AuthStatus.unknown;

        return GestureDetector(
          onTap: () => FocusScope.of(context).unfocus(),
          child: Scaffold(
            body: Stack(
              children: [
                // --- Fondo ---
                Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Theme.of(context).colorScheme.surface,
                        Theme.of(context).colorScheme.surfaceContainerHighest,
                      ],
                    ),
                  ),
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(24),
                      child: Card(
                        elevation: 4,
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 400),
                          padding: const EdgeInsets.all(32),
                          child: Form(
                            key: _formKey,
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Icon(
                                  Icons.engineering,
                                  size: 64,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                                const SizedBox(height: 24),
                                Text(
                                  "Mantenimiento",
                                  textAlign: TextAlign.center,
                                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: Theme.of(context).colorScheme.primary,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  "Acceso a técnicos y gestión",
                                  textAlign: TextAlign.center,
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Colors.grey[600],
                                  ),
                                ),
                                const SizedBox(height: 32),
                                
                                // --- Input Usuario ---
                                TextFormField(
                                  controller: _userController,
                                  focusNode: _userFocusNode,
                                  decoration: const InputDecoration(
                                    labelText: "Usuario",
                                    prefixIcon: Icon(Icons.person_outline),
                                    border: OutlineInputBorder(),
                                  ),
                                  textInputAction: TextInputAction.next,
                                  validator: (v) => (v?.isEmpty ?? true) ? "Requerido" : null,
                                  style: TextStyle(color: dynamicTextColor),
                                ),
                                const SizedBox(height: 16),
                                
                                // --- Input Contraseña ---
                                TextFormField(
                                  controller: _passController,
                                  obscureText: true,
                                  decoration: const InputDecoration(
                                    labelText: "Contraseña",
                                    prefixIcon: Icon(Icons.lock_outline),
                                    border: OutlineInputBorder(),
                                  ),
                                  textInputAction: TextInputAction.done,
                                  onFieldSubmitted: (_) => _onLoginPressed(),
                                  validator: (v) => (v?.isEmpty ?? true) ? "Requerido" : null,
                                  style: TextStyle(color: dynamicTextColor),
                                ),
                                const SizedBox(height: 24),
                                
                                // Botón Login
                                FilledButton(
                                  onPressed: _isLoading || isCheckingSession ? null : _onLoginPressed,
                                  style: FilledButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(vertical: 16),
                                  ),
                                  child: _isLoading
                                      ? const SizedBox(
                                          height: 20, 
                                          width: 20, 
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2, 
                                            color: Colors.white
                                          ),
                                        )
                                      : const Text("INICIAR SESIÓN"),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),

                // --- Splash ---
                if (isCheckingSession)
                  Container(
                    color: Colors.black54,
                    child: const Center(
                      child: CircularProgressIndicator(),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}