from django.db.models import Count
from search_history.models import HistoryModel
from rest_framework.views import APIView
from .serializer import CityStatSerializer
from rest_framework.response import Response


class TotalCitySearchedView(APIView):
    def get(self, request, *args, **kwargs):
        stats = (
            HistoryModel
            .objects.values('city')
            .annotate(count=Count('city'))
            .order_by('-count')
        )

        serializer = CityStatSerializer(stats, many=True)
        return Response(serializer.data)
