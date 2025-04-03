# class MiddlewareAuthenticationVerifyView(APIView):
#     authentication_classes = (MiddlewareAuthentication,)
#
#     def get(self, request):
#         return Response(UserBaseMinimumSerializer(request.user).data)
#
#
# class MiddlewareAssetAuthenticationVerifyView(APIView):
#     authentication_classes = (MiddlewareAssetAuthentication,)
#
#     def get(self, request):
#         return Response(UserBaseMinimumSerializer(request.user).data)
