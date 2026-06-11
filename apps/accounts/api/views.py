from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .serializers import ActiveFarmSerializer, LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Registro de nuevo usuario. Retorna tokens + datos del usuario."""

    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)


class LoginView(generics.GenericAPIView):
    """Login con email y password. Retorna tokens + datos del usuario."""

    serializer_class = LoginSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MeView(generics.RetrieveUpdateAPIView):
    """Obtener o actualizar el perfil del usuario autenticado."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ActiveFarmView(generics.GenericAPIView):
    """Cambiar la finca activa del usuario. Retorna el perfil actualizado."""

    serializer_class = ActiveFarmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
