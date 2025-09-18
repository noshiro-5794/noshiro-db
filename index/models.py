"""
Models Overview

This module defines the core database schema for a unified media catalog system using Django ORM.
It implements a Single Source of Truth (SSOT) for all catalog items, supporting multiple media types 
(anime, galgame, manga, game, novel, music, other) and their associated metadata, relationships, 
staff/character information, genres, episodes, and external sources.

Key Features:
- Subject-centric architecture: `Subject` serves as the root entity, linking specialized tables 
  (Anime, Galgame, etc.) via one-to-one relationships.
- Flexible model inheritance using abstract base classes (`Source`, `Staff`, `Character`, `CodeNameCombine`) 
  for common fields, timestamps, and source tracking.
- Relationship management: Supports subject-to-subject relationships (`SubjectRelation`), 
  staff/character roles in media (`AnimeStaffRelation`, `AnimeCharacterRelation`, etc.), and traits/genres.
- Source provenance: All key models track origin (`info_source`, `id_source`) and timestamps for auditing.
- Status & logging: `SubjectStatus` tracks errors, warnings, and resolutions for automated or manual corrections.
- Scheduled updates: `PendingUpdate` manages incremental synchronization tasks for subjects.
- Data integrity: Enforces uniqueness, constraints, and DB indexing for performance and consistency.
- Full traceability: All major models include `created_at` and `updated_at` timestamps.

Media-Specific Models:
- Anime: `Anime`, `AnimeStaff`, `AnimeCharacter`, `AnimeGenre`, `AnimeEpisode`
- Galgame: `Galgame`, `GalgameStaff`, `GalgameCharacter`, `GalgameProducer`, `GalgameGenre`
- Relations: Role and relationship tables for both Anime and Galgame

This schema provides a robust foundation for building a comprehensive, extensible, and auditable 
media catalog with rich metadata and relationships.
"""

import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex


class Source(models.Model):
    '''
    Source Model
    - Abstract base class for models with timestamp and source fields.

    Fields & Properties:
    | Name          | Type          | Description   |
    | ------------- | ------------- | ------------- |
    | info_source   | CharField     |               |
    | id_source     | CharField     |               |
    | created_at    | DateTimeField |               |
    | updated_at    | DateTimeField |               |
    '''

    info_source = models.CharField(max_length=64)
    id_source   = models.CharField(max_length=64)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['info_source', 'id_source']
        constraints = [
            models.UniqueConstraint(fields=['info_source', 'id_source'], name='uq_info_id_source')
        ]
        indexes = [
            models.Index(fields=['info_source', 'id_source'], name='idx_info_id_source'),
        ]


class CodeNameCombine(models.Model):
    '''
    CodeNameCombine Model
    - Abstract base class for models with code and name fields.

    Fields & Properties:
    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''

    code    = models.CharField(max_length=256)
    name    = models.CharField(max_length=256, blank=True)

    class Meta:
        abstract = True


class Staff(Source):
    '''
    Staff Model
    - Abstract base class for staff-related models.

    Fields & Properties:
    | Name          | Type                      | Description   |
    | ------------- | ------------------------- | ------------- |
    | name          | CharField                 |               |
    | description   | TextField                 |               |
    | gender        | CharField                 |               |
    | birth         | JSONField                 |               |
    | info_source   | CharField (Inherited)     |               |
    | id_source     | CharField (Inherited)     |               |
    | created_at    | DateTimeField (Inherited) |               |
    | updated_at    | DateTimeField (Inherited) |               |
    '''

    name        = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    gender      = models.CharField(max_length=64, blank=True)
    birth       = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True


class Character(Source):
    '''
    Character Model
    - Abstract base class for character-related models.

    Fields & Properties:
    | Name              | Type                      | Description   |
    | ----------------- | ------------------------- | ------------- |
    | name              | CharField                 |               |
    | image_original    | URLField                  |               |
    | image_thumbnail   | URLField                  |               |
    | description       | TextField                 |               |
    | gender            | CharField                 |               |
    | birth             | JSONField                 |               |
    | age               | IntegerField              |               |
    | height            | CharField                 |               |
    | weight            | CharField                 |               |
    | bwh               | JSONField                 |               |
    | blood_type        | CharField                 |               |
    | info_source       | CharField (Inherited)     |               |
    | id_source         | CharField (Inherited)     |               |
    | created_at        | DateTimeField (Inherited) |               |
    | updated_at        | DateTimeField (Inherited) |               |
    '''

    name            = models.CharField(max_length=256, blank=True)
    image_original  = models.URLField(max_length=1024, blank=True)
    image_thumbnail = models.URLField(max_length=1024, blank=True)
    description     = models.TextField(blank=True)
    gender          = models.CharField(max_length=64, blank=True)
    birth           = models.JSONField(default=dict, blank=True)
    age             = models.IntegerField(blank=True, null=True)
    height          = models.CharField(max_length=64, blank=True)
    weight          = models.CharField(max_length=64, blank=True)
    bwh             = models.JSONField(default=dict, blank=True)
    blood_type      = models.CharField(max_length=64, blank=True)

    class Meta:
        abstract = True


class SubjectStatus(models.Model):
    '''
    SubjectStatus Model
    - Stores the *current* status of a Subject.

    | Name          | Type          | Description   |
    | ------------- | ------------- | ------------- |
    | subject       | OneToOneField |               |
    | severity      | CharField     |               |
    | headline      | CharField     |               |
    | detail        | TextField     |               |
    | is_resolved   | BooleanField  |               |
    | is_locked     | BooleanField  |               |
    | updated_at    | DateTimeField |               |
    '''

    SEVERITY_CHOICES = [
        ('info',    'Info'),
        ('warning', 'Warning'),
        ('error',   'Error'),
    ]

    subject     = models.OneToOneField("Subject", on_delete=models.CASCADE, related_name="status")
    severity    = models.CharField(max_length=64, choices=SEVERITY_CHOICES)
    headline    = models.CharField(max_length=256, blank=True)
    detail      = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    is_locked   = models.BooleanField(default=False)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subject_status'
        indexes = [
            models.Index(fields=["severity"]),
            models.Index(fields=["headline"]),
            models.Index(fields=["is_resolved"]),
            models.Index(fields=["is_locked"]),
        ]

    def __str__(self):
        return f"{self.subject} [{self.severity}] {'LOCKED' if self.is_locked else ''}"


class Subject(Source):
    '''
    Subject Model
    - The top-level entity and SSOT for all sub-entities in the catalog.
    - Holds only the parent-level attributes that are common to all subject types.
    - Shares its primary key with child tables (via one-to-one relations), keeping the entire catalog unified.

    Fields & Properties:
    | Name              | Type                      | Description                       |
    | ----------------- | ------------------------- | --------------------------------- |
    | id                | UUIDField                 |                                   |
    | subject_type      | CharField                 |                                   |
    | title             | CharField                 |                                   |
    | date              | DateField                 |                                   |
    | ambiguous_date    | DateField                 | Only if "date" is not available.  |
    | image_original    | URLField                  |                                   |
    | image_thumbnail   | URLField                  |                                   |
    | description       | TextField                 |                                   |
    | nsfw              | BooleanField              |                                   |
    | infobox           | JSONField                 |                                   |
    | tags              | JSONField                 |                                   |
    | info_source       | CharField (Inherited)     |                                   |
    | id_source         | CharField (Inherited)     |                                   |
    | created_at        | DateTimeField (Inherited) |                                   |
    | updated_at        | DateTimeField (Inherited) |                                   |
    | status            | OneToOneField (Reverse)   | Current status and log (if any).  |
    '''
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    SUBJECT_TYPES = [
        ('anime',   'Anime'),
        ('galgame', 'Galgame'),
        ('manga',   'Manga'),
        ('game',    'Game'),
        ('novel',   'Novel'),
        ('music',   'Music'),
        ('other',   'Other'),
    ]

    subject_type    = models.CharField(max_length=64, choices=SUBJECT_TYPES)
    title           = models.CharField(max_length=256, blank=True)
    date            = models.DateField(blank=True, null=True)
    ambiguous_date  = models.DateField(blank=True, null=True)
    image_original  = models.URLField(max_length=1024, blank=True)
    image_thumbnail = models.URLField(max_length=1024, blank=True)
    description     = models.TextField(blank=True)
    nsfw            = models.BooleanField(default=False)
    infobox         = models.JSONField(default=list, blank=True)
    tags            = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'subject'
        ordering = ['-date', 'title']
        indexes = [
            models.Index(fields=['title'], name='idx_subject_title')
        ]

    def __str__(self):
        return f'[{self.subject_type}] {self.title or "Untitled"} ({self.date or self.ambiguous_date or "Unknown"})'


class SubjectRelationType(CodeNameCombine):
    '''
    SubjectRelationType Model
    - Stores the types of relationships between different Subject entities.

    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''

    class Meta:
        db_table = 'subject_relation_type'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_subject_relation_type_code")
        ]

    def __str__(self):
        return self.name or self.code


class SubjectRelation(models.Model):
    '''
    SubjectRelation Model
    - Defines a directed relationship between two Subject entities.

    | Name      | Type          | Description   |
    | --------- | ------------- | ------------- |
    | source    | ForeignKey    |               |
    | target    | ForeignKey    |               |
    | type      | ForeignKey    |               |
    '''

    source  = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='outgoing_relations')
    target  = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='incoming_relations')
    type    = models.ForeignKey(SubjectRelationType, on_delete=models.PROTECT)

    class Meta:
        db_table = 'subject_relation'

    def __str__(self):
        return f'{self.source} -> {self.target}'


class AnimeStaff(Staff):
    '''
    AnimeStaff Model
    - Stores comprehensive information about anime staff.

    Fields & Properties:
    | Name          | Type                      | Description   |
    | ------------- | ------------------------- | ------------- |
    | type          | CharField                 |               |
    | career        | CharField                 |               |
    | name          | CharField (Inherited)     |               |
    | description   | TextField (Inherited)     |               |
    | gender        | CharField (Inherited)     |               |
    | birth         | JSONField (Inherited)     |               |
    | info_source   | CharField (Inherited)     |               |
    | id_source     | CharField (Inherited)     |               |
    | created_at    | DateTimeField (Inherited) |               |
    | updated_at    | DateTimeField (Inherited) |               |
    | characters    | ManyToManyField (Reverse) |               |
    | animes        | ManyToManyField (Reverse) |               |
    '''

    type        = models.CharField(max_length=64, blank=True)
    career      = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = 'anime_staff'
        ordering = ['name']

    def __str__(self):
        return self.name


class AnimeCharacter(Character):
    '''
    AnimeCharacter Model
    - Stores comprehensive information about anime characters.

    Fields & Properties:
    | Name              | Type                      | Description   |
    | ----------------- | ------------------------- | ------------- |
    | actors            | ManyToManyField           |               |
    | name              | CharField  (Inherited)    |               |
    | image_original    | URLField (Inherited)      |               |
    | image_thumbnail   | URLField (Inherited)      |               |
    | description       | TextField (Inherited)     |               |
    | gender            | CharField (Inherited)     |               |
    | birth             | JSONField (Inherited)     |               |
    | age               | IntegerField (Inherited)  |               |
    | height            | CharField (Inherited)     |               |
    | weight            | CharField (Inherited)     |               |
    | bwh               | JSONField (Inherited)     |               |
    | blood_type        | CharField (Inherited)     |               |
    | info_source       | CharField (Inherited)     |               |
    | id_source         | CharField (Inherited)     |               |
    | created_at        | DateTimeField (Inherited) |               |
    | updated_at        | DateTimeField (Inherited) |               |
    | animes            | ManyToManyField (Reverse) |               |
    '''

    actors = models.ManyToManyField('AnimeStaff', related_name='characters', blank=True)

    class Meta:
        db_table = 'anime_character'
        ordering = ['name']

    def __str__(self):
        return self.name


class AnimeGenre(CodeNameCombine):
    '''
    AnimeGenre Model
    - Stores genres for Anime.
    - Provides a mapping from original genre names to standardized role names.

    Fields & Properties:
    | Name      | Type                      | Description   |
    | --------- | ------------------------- | ------------- |
    | code      | CharField                 |               |
    | name      | CharField                 |               |
    | animes    | ManyToManyField (Reverse) |               |
    '''

    class Meta:
        db_table = 'anime_genre'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_anime_genre_code")
        ]

    def __str__(self):
        return self.name or self.code


class AnimeEpisode(Source):
    '''
    AnimeEpisode Model
    - Stores episode information for Anime.
    - Each episode belongs to exactly one Anime

    Fields & Properties:
    | Name          | Type                      | Description   |
    | ------------- | ------------------------- | ------------- |
    | title         | CharField                 |               |
    | type          | CharField                 |               |
    | ep_num        | IntegerField              |               |
    | duration      | DurationField             |               |
    | airdate       | DateField                 |               |
    | description   | TextField                 |               |
    | anime         | ForeignKey                |               |
    | info_source   | CharField (Inherited)     |               |
    | id_source     | CharField (Inherited)     |               |
    | created_at    | DateTimeField (Inherited) |               |
    | updated_at    | DateTimeField (Inherited) |               |
    '''

    title       = models.CharField(max_length=256, blank=True)
    type        = models.CharField(max_length=64, blank=True)
    ep_num      = models.IntegerField(blank=True, null=True)
    duration    = models.DurationField(blank=True, null=True)
    airdate     = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    anime       = models.ForeignKey('Anime', on_delete=models.CASCADE, related_name='episodes')

    class Meta:
        db_table = 'anime_episode'
        ordering = ['anime', 'type', 'ep_num']

    def __str__(self):
        return self.title


class Anime(Source):
    '''
    Anime Model
    - Stores detailed information related to `Subject` entries of type "anime".

    Fields & Properties:
    | Name              | Type                      | Description                   |
    | ----------------- | ------------------------- | ----------------------------- |
    | subject           | OneToOneField             |                               |
    | aliases           | JSONField                 |                               |
    | start_date        | DateField                 |                               |
    | end_date          | DateField                 |                               |
    | anime_type        | CharField                 | (e.g., "TV", "OVA")           |
    | anime_source      | CharField                 | (e.g., "Manga", "Original")   |
    | official_websites | JSONField                 |                               |
    | description       | TextField                 |                               |
    | image_original    | URLField                  |                               |
    | image_thumbnail   | URLField                  |                               |
    | image_extra       | JSONField                 |                               |
    | anime_status      | CharField                 |                               |
    | ep_total          | IntegerField              |                               |
    | broadcast         | JSONField                 |                               |
    | broadcast_season  | JSONField                 |                               |
    | external_links    | JSONField                 |                               |
    | staff             | ManyToManyField           |                               |
    | characters        | ManyToManyField           |                               |
    | genres            | ManyToManyField           |                               |
    | info_source       | CharField (Inherited)     |                               |
    | id_source         | CharField (Inherited)     |                               |
    | created_at        | DateTimeField (Inherited) |                               |
    | updated_at        | DateTimeField (Inherited) |                               |
    | episodes          | ForeignKey (Reverse)      |                               |
    '''

    subject = models.OneToOneField(
        Subject,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='anime'
    )

    aliases             = ArrayField(models.CharField(max_length=256), default=list, blank=True)
    titles              = models.JSONField(default=dict, blank=True)
    start_date          = models.DateField(blank=True, null=True)
    end_date            = models.DateField(blank=True, null=True)
    anime_type          = models.CharField(max_length=64, blank=True)
    anime_source        = models.CharField(max_length=64, blank=True)
    official_websites   = models.JSONField(default=list, blank=True)
    description         = models.TextField(blank=True)
    image_original      = models.URLField(max_length=1024, blank=True)
    image_thumbnail     = models.URLField(max_length=1024, blank=True)
    image_extra         = models.JSONField(default=list, blank=True)
    anime_status        = models.CharField(max_length=256, blank=True)
    ep_total            = models.IntegerField(blank=True, null=True)
    broadcast           = models.JSONField(default=dict, blank=True)
    broadcast_season    = models.JSONField(default=dict, blank=True)
    external_links      = models.JSONField(default=dict, blank=True)
    staff               = models.ManyToManyField('AnimeStaff', through='AnimeStaffRelation', related_name='animes', blank=True)
    characters          = models.ManyToManyField('AnimeCharacter', through='AnimeCharacterRelation', related_name='animes', blank=True)
    genres              = models.ManyToManyField('AnimeGenre', related_name='animes', blank=True)

    class Meta:
        db_table = 'anime'
        ordering = ['-subject__date', 'subject__title']
        indexes = [
            GinIndex(fields=['aliases'], name='idx_anime_aliases')
        ]

    def __str__(self):
        return self.subject.title


class AnimeStaffRelationRole(CodeNameCombine):
    '''
    AnimeStaffRelationRole Model
    - Stores roles for AnimeStaff related to Anime.

    Fields & Properties:
    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''

    class Meta:
        db_table = 'anime_staff_relation_role'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_anime_staff_relation_role_code")
        ]

    def __str__(self):
        return self.name or self.code


class AnimeStaffRelation(models.Model):
    '''
    AnimeStaffRelation Model
    - Represents the relationship between Anime and AnimeStaff.

    Fields & Properties:
    | Name          | Type          | Description   |
    | ------------- | ------------- | ------------- |
    | anime         | ForeignKey    |               |
    | staff         | ForeignKey    |               |
    | role          | ForeignKey    |               |
    | description   | TextField     |               |
    '''

    anime       = models.ForeignKey(Anime, on_delete=models.CASCADE)
    staff       = models.ForeignKey(AnimeStaff, on_delete=models.CASCADE)
    role        = models.ForeignKey(AnimeStaffRelationRole, on_delete=models.PROTECT)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'anime_staff_relation'
        ordering = ['anime', 'staff']
        constraints = [
            models.UniqueConstraint(fields=['anime', 'staff', 'role'], name='uq_anime_staff_role')
        ]

    def __str__(self):
        return f'{self.anime} - {self.staff} ({self.role})'


class AnimeCharacterRelationRole(CodeNameCombine):
    '''
    AnimeCharacterRelationRole Model
    - Stores roles for AnimeCharacter related to Anime.

    Fields & Properties:
    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''

    class Meta:
        db_table = 'anime_character_relation_role'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_anime_character_relation_role_code")
        ]

    def __str__(self):
        return self.name or self.code


class AnimeCharacterRelation(models.Model):
    '''
    AnimeCharacterRelation Model
    - Represents the ralationship between Anime and AnimeCharacter.

    Fields & Properties:
    | Name          | Type          | Description   |
    | ------------- | ------------- | ------------- |
    | anime         | ForeignKey    |               |
    | character     | ForeignKey    |               |
    | role          | ForeignKey    |               |
    | description   | TextField     |               |
    '''

    anime       = models.ForeignKey(Anime, on_delete=models.CASCADE)
    character   = models.ForeignKey(AnimeCharacter, on_delete=models.CASCADE)
    role        = models.ForeignKey(AnimeCharacterRelationRole, on_delete=models.PROTECT)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'anime_character_relation'
        ordering = ['anime', 'character']
        constraints = [
            models.UniqueConstraint(fields=['anime', 'character', 'role'], name='uq_anime_character_role')
        ]

    def __str__(self):
        return f'{self.anime} - {self.character} ({self.role})'


class GalgameProducer(Source):
    '''
    GalgameProducer Model
    - 

    Fields & Properties
    | Name              | Type                      | Description   |
    | ----------------- | ------------------------- | ------------- |
    | name              | CharField                 |               |
    | aliases           | JSONField                 |               |
    | type              | CharField                 |               |
    | description       | TextField                 |               |
    | official_website  | URLField                  |               |
    | external_link     | JSONField                 |               |
    | info_source       | CharField (Inherited)     |               |
    | id_source         | CharField (Inherited)     |               |
    | created_at        | DateTimeField (Inherited) |               |
    | updated_at        | DateTimeField (Inherited) |               |
    '''

    name                = models.CharField(max_length=256, blank=True)
    aliases             = models.JSONField(default=list, blank=True)
    type                = models.CharField(max_length=64, blank=True)
    description         = models.TextField(blank=True)
    official_website    = models.URLField(max_length=1024, blank=True)
    external_link       = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'galgame_producer'
        ordering = ['name']

    def __str__(self):
        return self.name


class GalgameStaff(Staff):
    '''
    GalgameStaff Model
    - 

    Fields & Properties
    | Name          | Type                      | Description   |
    | ------------- | ------------------------- | ------------- |
    | aliases       | JSONField                 |               |
    | external_link | JSONField                 |               |
    | name          | CharField (Inherited)     |               |
    | description   | TextField (Inherited)     |               |
    | gender        | CharField (Inherited)     |               |
    | birth         | JSONField (Inherited)     |               |
    | info_source   | CharField (Inherited)     |               |
    | id_source     | CharField (Inherited)     |               |
    | created_at    | DateTimeField (Inherited) |               |
    | updated_at    | DateTimeField (Inherited) |               |
    '''

    aliases         = models.JSONField(default=list, blank=True)
    external_link   = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'galgame_staff'
        ordering = ['name']

    def __str__(self):
        return self.name


class GalgameCharacterTrait(CodeNameCombine):
    '''
    GalgameCharacterTrait Model
    - 

    Fields & Properties:
    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''
    
    class Meta:
        db_table = 'galgame_character_trait'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_galgame_character_trait_code")
        ]

    def __str__(self):
        return self.name or self.code


class GalgameCharacter(Character):
    '''
    GalgameCharacter Model
    - 

    Fields & Properties:
    | Name              | Type                      | Description   |
    | ----------------- | ------------------------- | ------------- |
    | traits            | ManyToManyField           |               |
    | actors            | OneToOneField             |               |
    | name              | CharField (Inherited)     |               |
    | image_original    | URLField (Inherited)      |               |
    | image_thumbnail   | URLField (Inherited)      |               |
    | description       | TextField (Inherited)     |               |
    | gender            | CharField (Inherited)     |               |
    | birth             | JSONField (Inherited)     |               |
    | age               | IntegerField (Inherited)  |               |
    | height            | CharField (Inherited)     |               |
    | weight            | CharField (Inherited)     |               |
    | bwh               | JSONField (Inherited)     |               |
    | blood_type        | CharField (Inherited)     |               |
    | info_source       | CharField (Inherited)     |               |
    | id_source         | CharField (Inherited)     |               |
    | created_at        | DateTimeField (Inherited) |               |
    | updated_at        | DateTimeField (Inherited) |               |
    '''

    traits  = models.ManyToManyField(GalgameCharacterTrait, related_name='characters', blank=True)
    actors  = models.ManyToManyField(GalgameStaff, related_name='characters', blank=True)

    class Meta:
        db_table = 'galgame_character'
        ordering = ['name']

    def __str__(self):
        return self.name


class GalgameGenre(CodeNameCombine):
    '''
    GalgameGenre Model
    - 

    Fields & Properties:
    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''

    class Meta:
        db_table = 'galgame_genre'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_galgame_genre_code")
        ]

    def __str__(self):
        return self.name or self.code


class Galgame(Source):
    '''
    Galgame Model
    - Stores detailed information related to `Subject` entries of type "galgame".

    Fields & Properties:
    | Name              | Type                      | Description   |
    | ----------------- | ------------------------- | ------------- |
    | subject           | OneToOneField             |               |
    | aliases           | ArrayField                |               |
    | titles            | JSONField                 |               |
    | released_date     | DateField                 |               |
    | description       | TextField                 |               |
    | image_original    | URLField                  |               |
    | image_thumbnail   | URLField                  |               |
    | screenshots       | URLField                  |               |
    | platforms         | JSONField                 |               |
    | galgame_status    | CharField                 |               |
    | external_links    | JSONField                 |               |
    | producers         | ManyToManyField           |               |
    | staff             | ManyToManyField           |               |
    | characters        | ManyToManyField           |               |
    | genres            | ManyToManyField           |               |
    | info_source       | CharField (Inherited)     |               |
    | id_source         | CharField (Inherited)     |               |
    | created_at        | DateTimeField (Inherited) |               |
    | updated_at        | DateTimeField (Inherited) |               |
    '''

    subject = models.OneToOneField(
        Subject,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='galgame'
    )

    aliases         = ArrayField(models.CharField(max_length=256), default=list, blank=True)
    titles          = models.JSONField(default=dict, blank=True)
    released_date   = models.DateField(blank=True, null=True)
    description     = models.TextField(blank=True)
    image_original  = models.URLField(max_length=1024, blank=True)
    image_thumbnail = models.URLField(max_length=1024, blank=True)
    screenshots     = models.URLField(max_length=1024, blank=True)
    platforms       = models.JSONField(default=list, blank=True)
    galgame_status  = models.CharField(max_length=64, blank=True)
    external_links  = models.JSONField(default=list, blank=True)
    producers       = models.ManyToManyField(GalgameProducer, related_name='galgames', blank=True)
    staff           = models.ManyToManyField(GalgameStaff, through='GalgameStaffRelation', related_name='galgames', blank=True)
    characters      = models.ManyToManyField(GalgameCharacter, through='GalgameCharacterRelation', related_name='galgames', blank=True)
    genres          = models.ManyToManyField(GalgameGenre, related_name='galgames', blank=True)

    class Meta:
        db_table = 'galgame'
        ordering = ['-subject__date', 'subject__title']
        constraints = [
            models.UniqueConstraint(fields=['info_source', 'id_source'], name='uq_galgame_source')
        ]
        indexes = [
            models.Index(fields=['id_source'], name='idx_galgame_staff_source'),
            GinIndex(fields=['aliases'], name='idx_galgame_aliases')
        ]

    def __str__(self):
        return self.subject.title


class GalgameStaffRelationRole(CodeNameCombine):
    '''
    GalgameStaffRelationRole Model
    - Stores roles for GalgameStaff related to Galgame.

    Fields & Properties:
    | Name  | Type      | Description   |
    | ----- | --------- | ------------- |
    | code  | CharField |               |
    | name  | CharField |               |
    '''

    class Meta:
        db_table = 'galgame_staff_relation_role'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_galgame_staff_relation_role_code")
        ]
    
    def __str__(self):
        return self.name or self.code


class GalgameStaffRelation(models.Model):
    '''
    GalgameStaffRelation Model
    - 

    Fields & Properties:
    | Name  | Type  | Description   |
    | ----- | ----- | ------------- |
    '''

    galgame     = models.ForeignKey(Galgame, on_delete=models.CASCADE)
    staff       = models.ForeignKey(GalgameStaff, on_delete=models.CASCADE)
    role        = models.ForeignKey(GalgameStaffRelationRole, on_delete=models.PROTECT)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'galgame_staff_relation'
        ordering = ['galgame', 'staff']
        constraints = [
            models.UniqueConstraint(fields=['galgame', 'staff', 'role'], name='uq_galgame_staff_role')
        ]

    def __str__(self):
        return f'{self.galgame} - {self.staff} ({self.role})'


class GalgameCharacterRelation(models.Model):
    '''
    GalgameCharacterRelation Model
    - 

    Fields & Properties:
    | Name  | Type  | Description   |
    | ----- | ----- | ------------- |
    '''

    galgame     = models.ForeignKey(Galgame, on_delete=models.CASCADE)
    character   = models.ForeignKey(GalgameCharacter, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'galgame_character_relation'
        ordering = ['galgame', 'character']
        constraints = [
            models.UniqueConstraint(fields=['galgame', 'character'], name='uq_galgame_character')
        ]

    def __str__(self):
        return f'{self.galgame} - {self.character}'


class PendingUpdate(models.Model):
    '''
    PendingUpdate Model
    - Represents a scheduled update or synchronization task for a Subject entity.

    Fields & Properties:
    | Name              | Type          | Description   |
    | ----------------- | ------------- | ------------- |
    | subject           | ForeignKey    |               |
    | next_update_time  | DateTimeField |               |
    | task_type         | CharField     |               |
    | attempt_count     | IntegerField  |               |
    | latest_log        | TextField     |               |
    | created_at        | DateTimeField |               |
    | updated_at        | DateTimeField |               |
    '''

    subject             = models.ForeignKey(Subject, on_delete=models.CASCADE)
    next_update_time    = models.DateTimeField()
    task_type           = models.CharField(max_length=64)
    attempt_count       = models.IntegerField(default=0)
    latest_log          = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pending_update'
        constraints = [
            models.UniqueConstraint(fields=['subject'], name='uq_pending_update_subject')
        ]
        indexes = [
            models.Index(fields=['next_update_time'])
        ]
    
    def __str__(self):
        return f'{self.subject.title} - {self.task_type} - {self.next_update_time}'