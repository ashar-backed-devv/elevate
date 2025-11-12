from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Domain, Course, Announcement, Chapter, Subtopic, Flashcard, Question

class ChapterByNameAndCourseWidget(ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        course_name = row.get('course')
        return self.model.objects.filter(
            name=value,
            course__name=course_name
        )

# Handles duplicate subtopics with same name under different chapters (and courses)
class SubtopicByNameChapterCourseWidget(ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        chapter_name = row.get('chapter')
        course_name = row.get('course')
        return self.model.objects.filter(
            name=value,
            chapter__name=chapter_name,
            chapter__course__name=course_name
        )

# -------------------
# Resources (define import/export structure)
# -------------------

class DomainResource(resources.ModelResource):
    class Meta:
        model = Domain
        fields = ('id', 'name',)
        import_id_fields = ('name',)  # Used for matching existing domains by name


class CourseResource(resources.ModelResource):
    domain = fields.Field(
        column_name='domain',
        attribute='domain',
        widget=ForeignKeyWidget(Domain, field='name')  # use domain name instead of ID
    )

    class Meta:
        model = Course
        fields = (
            'id', 'domain', 'name',
            'about_primary', 'about_secondary',
            'total_questions', 'total_chapters'
        )
        import_id_fields = ('name',)  # uniquely identifies a record


class AnnouncementResource(resources.ModelResource):
    course = fields.Field(
        column_name='course',
        attribute='course',
        widget=ForeignKeyWidget(Course, field='name')
    )

    class Meta:
        model = Announcement
        fields = ('id', 'course', 'primary_text', 'secondary_text')


class ChapterResource(resources.ModelResource):
    course = fields.Field(
        column_name='course',
        attribute='course',
        widget=ForeignKeyWidget(Course, field='name')
    )

    class Meta:
        model = Chapter
        fields = ('id', 'course', 'name')
        import_id_fields = ('course', 'name')


class SubtopicResource(resources.ModelResource):
    chapter = fields.Field(
        column_name='chapter',
        attribute='chapter',
        widget=ChapterByNameAndCourseWidget(Chapter, 'name')
    )

    class Meta:
        model = Subtopic
        fields = ('id', 'chapter', 'name')
        import_id_fields = ('chapter', 'name')


class FlashcardResource(resources.ModelResource):
    subtopic = fields.Field(
        column_name='subtopic',
        attribute='subtopic',
        widget=SubtopicByNameChapterCourseWidget(Subtopic, 'name')
    )

    class Meta:
        model = Flashcard
        fields = ('id', 'subtopic', 'primary_text', 'secondary_text')
        import_id_fields = ('subtopic', 'primary_text', 'secondary_text')


class QuestionResource(resources.ModelResource):
    subtopic = fields.Field(
        column_name='subtopic',
        attribute='subtopic',
        widget=SubtopicByNameChapterCourseWidget(Subtopic, 'name')
    )

    class Meta:
        model = Question
        fields = (
            'id', 'subtopic', 'text',
            'option0', 'option1', 'option2', 'option3',
            'correct_option', 'explanation'
        )
        import_id_fields = ('subtopic', 'text')

# -------------------
# Admin Registrations (with import/export support)
# -------------------

@admin.register(Domain)
class DomainAdmin(ImportExportModelAdmin):
    resource_class = DomainResource


@admin.register(Course)
class CourseAdmin(ImportExportModelAdmin):
    resource_class = CourseResource


@admin.register(Announcement)
class AnnouncementAdmin(ImportExportModelAdmin):
    resource_class = AnnouncementResource


@admin.register(Chapter)
class ChapterAdmin(ImportExportModelAdmin):
    resource_class = ChapterResource


@admin.register(Subtopic)
class SubtopicAdmin(ImportExportModelAdmin):
    resource_class = SubtopicResource


@admin.register(Flashcard)
class FlashcardAdmin(ImportExportModelAdmin):
    resource_class = FlashcardResource


@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin):
    resource_class = QuestionResource
