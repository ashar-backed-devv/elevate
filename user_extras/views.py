from rest_framework import viewsets, permissions
from .models import Favorite, Notification, ChatMessage
from content.models import Flashcard
from .serializers import FavoriteSerializer, NotificationSerializer, ChatMessageSerializer
from content.serializers import FlashcardSerializer
import tempfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .chatbot_core import process_pdf_book, delete_namespace, search_book, llm_chain, INDEX_NAME

class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # 👇 Custom endpoint: get favorited flashcards (with details) for a course
    @action(detail=False, methods=['get'], url_path='course/(?P<course_id>[^/.]+)')
    def get_favorites_by_course(self, request, course_id=None):
        favorites = Favorite.objects.filter(user=request.user, course_id=course_id)
        flashcard_ids = favorites.values_list('flashcard_id', flat=True)
        flashcards = Flashcard.objects.filter(id__in=flashcard_ids)
        serializer = FlashcardSerializer(flashcards, many=True)
        return Response(serializer.data)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatMessage.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # 👇 Custom action to get messages for a specific course
    @action(detail=False, methods=['get'], url_path='course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        """Return all chat messages for the given course belonging to the logged-in user"""
        messages = ChatMessage.objects.filter(user=request.user, course_id=course_id).order_by('timestamp')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

class AdminProcessPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pdf_file = request.FILES.get('pdf')
        namespace = request.data.get('course_id')
        if not pdf_file or not namespace:
            return Response({'error': 'pdf and course_id are required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in pdf_file.chunks():
                tmp.write(chunk)
            pdf_path = tmp.name
        try:
            process_pdf_book(pdf_path, namespace)
            return Response({'status': f'Processed successfully for {namespace}'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminDeleteNamespaceView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request):
        namespace = request.data.get('course_id')
        if not namespace:
            return Response({'error': 'course_id is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            delete_namespace(INDEX_NAME, namespace)
            return Response({'status': f'Namespace {namespace} deleted successfully.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatbotQueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        namespace = request.data.get('course_id')
        query = request.data.get('query')
        if not namespace or not query:
            return Response({'error': 'course_id and query are required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            results = search_book(query, namespace)
            if not results:
                return Response({'response': "No relevant info found."})
            context = [doc.page_content for doc in results]
            response = llm_chain.invoke({"context": context, "question": query})
            return Response({'response': response})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
