from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class CalculateDistanceRequest(_message.Message):
    __slots__ = ("date", "device_id")
    DATE_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    date: str
    device_id: str
    def __init__(self, date: str | None = ..., device_id: str | None = ...) -> None: ...

class CalculateDistanceResponse(_message.Message):
    __slots__ = ("job_id", "status", "queued_at")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    QUEUED_AT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    queued_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        job_id: str | None = ...,
        status: str | None = ...,
        queued_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GetJobStatusRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: str | None = ...) -> None: ...

class GetJobStatusResponse(_message.Message):
    __slots__ = (
        "job_id",
        "status",
        "queued_at",
        "started_at",
        "completed_at",
        "error_message",
        "result",
    )
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    QUEUED_AT_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    queued_at: _timestamp_pb2.Timestamp
    started_at: _timestamp_pb2.Timestamp
    completed_at: _timestamp_pb2.Timestamp
    error_message: str
    result: JobResult
    def __init__(
        self,
        job_id: str | None = ...,
        status: str | None = ...,
        queued_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        started_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        completed_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        error_message: str | None = ...,
        result: JobResult | _Mapping | None = ...,
    ) -> None: ...

class ListJobsRequest(_message.Message):
    __slots__ = ("status", "limit", "offset", "date", "device_id")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    status: str
    limit: int
    offset: int
    date: str
    device_id: str
    def __init__(
        self,
        status: str | None = ...,
        limit: int | None = ...,
        offset: int | None = ...,
        date: str | None = ...,
        device_id: str | None = ...,
    ) -> None: ...

class ListJobsResponse(_message.Message):
    __slots__ = ("jobs", "total_count", "limit", "offset")
    JOBS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    jobs: _containers.RepeatedCompositeFieldContainer[JobSummary]
    total_count: int
    limit: int
    offset: int
    def __init__(
        self,
        jobs: _Iterable[JobSummary | _Mapping] | None = ...,
        total_count: int | None = ...,
        limit: int | None = ...,
        offset: int | None = ...,
    ) -> None: ...

class JobSummary(_message.Message):
    __slots__ = ("job_id", "status", "date", "device_id", "queued_at", "completed_at")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    QUEUED_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    date: str
    device_id: str
    queued_at: _timestamp_pb2.Timestamp
    completed_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        job_id: str | None = ...,
        status: str | None = ...,
        date: str | None = ...,
        device_id: str | None = ...,
        queued_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
        completed_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class JobResult(_message.Message):
    __slots__ = (
        "csv_path",
        "total_distance_km",
        "total_locations",
        "max_distance_km",
        "min_distance_km",
        "date",
        "device_id",
        "processing_time_ms",
    )
    CSV_PATH_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LOCATIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    MIN_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    csv_path: str
    total_distance_km: float
    total_locations: int
    max_distance_km: float
    min_distance_km: float
    date: str
    device_id: str
    processing_time_ms: int
    def __init__(
        self,
        csv_path: str | None = ...,
        total_distance_km: float | None = ...,
        total_locations: int | None = ...,
        max_distance_km: float | None = ...,
        min_distance_km: float | None = ...,
        date: str | None = ...,
        device_id: str | None = ...,
        processing_time_ms: int | None = ...,
    ) -> None: ...
