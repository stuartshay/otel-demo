from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CalculateDistanceRequest(_message.Message):
    __slots__ = ("date", "device_id")
    DATE_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    date: str
    device_id: str
    def __init__(self, date: _Optional[str] = ..., device_id: _Optional[str] = ...) -> None: ...

class CalculateDistanceResponse(_message.Message):
    __slots__ = ("job_id", "status", "queued_at")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    QUEUED_AT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    queued_at: _timestamp_pb2.Timestamp
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[str] = ..., queued_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetJobStatusRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class GetJobStatusResponse(_message.Message):
    __slots__ = ("job_id", "status", "queued_at", "started_at", "completed_at", "error_message", "result")
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
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[str] = ..., queued_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., started_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., completed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., error_message: _Optional[str] = ..., result: _Optional[_Union[JobResult, _Mapping]] = ...) -> None: ...

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
    def __init__(self, status: _Optional[str] = ..., limit: _Optional[int] = ..., offset: _Optional[int] = ..., date: _Optional[str] = ..., device_id: _Optional[str] = ...) -> None: ...

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
    def __init__(self, jobs: _Optional[_Iterable[_Union[JobSummary, _Mapping]]] = ..., total_count: _Optional[int] = ..., limit: _Optional[int] = ..., offset: _Optional[int] = ...) -> None: ...

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
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[str] = ..., date: _Optional[str] = ..., device_id: _Optional[str] = ..., queued_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., completed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class JobResult(_message.Message):
    __slots__ = ("csv_path", "total_distance_km", "total_locations", "max_distance_km", "min_distance_km", "date", "device_id", "processing_time_ms")
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
    def __init__(self, csv_path: _Optional[str] = ..., total_distance_km: _Optional[float] = ..., total_locations: _Optional[int] = ..., max_distance_km: _Optional[float] = ..., min_distance_km: _Optional[float] = ..., date: _Optional[str] = ..., device_id: _Optional[str] = ..., processing_time_ms: _Optional[int] = ...) -> None: ...
