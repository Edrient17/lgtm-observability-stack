# 기술 조사 및 도입 판단

본 문서는 현재 팀에서 사용 중인 ELK + Wazuh + Kafka, Zabbix, PinPoint 체계를 전제로, 이번 프로젝트에서 검토한 Loki, Promtail, Prometheus, Tempo, OpenTelemetry Collector, Grafana 기반 LGTM 구성을 어떤 상황에서 도입하면 좋은지 판단하기 위한 비교 분석이다.

## 1. 전제

LGTM은 기존 도구를 무조건 대체하는 스택이라기보다, Kubernetes와 MSA 환경에서 로그, 메트릭, 트레이스를 Grafana 중심으로 연결해 장애 원인 분석 시간을 줄이는 관측성 스택으로 보는 것이 적절하다.

## 2. 로그: ELK vs Loki + Promtail

현재 팀의 로그 체계는 ELK + Wazuh + Kafka 부하분산 구조를 통해 로그와 보안 로그를 수집하고 있으며, 수집량이 많아 고도화가 진행 중인 상태로 이해된다. 이 구조는 보안 분석과 자유 검색에는 강하지만, 인덱스 비용과 운영 튜닝 부담이 커질 수 있다.

| 비교 항목 | ELK + Wazuh + Kafka | Loki + Promtail |
| --- | --- | --- |
| 주요 목적 | 로그 전문 검색, 보안 로그 분석, 다양한 로그 포맷 정규화 | 서비스, namespace, pod 같은 label로 범위를 좁힌 뒤 장애 분석용 로그 조회 |
| 검색 방식 | Elasticsearch가 로그 필드와 본문을 적극적으로 인덱싱하여 KQL, Lucene, Query DSL 기반 자유 검색에 강함 | Loki는 로그 본문 전체를 인덱싱하지 않고 label 중심으로 stream을 찾은 뒤 LogQL로 문자열, JSON, regex 검색 |
| 수집/정규화 | Kafka, Logstash, Beats, Elastic Agent, Wazuh와 결합해 대량 수집 및 보안 이벤트 처리에 유리 | Promtail이 Docker/Kubernetes 로그를 tail하고 label 및 trace_id 등을 추출해 Loki로 push |
| 비용/운영 | 검색 성능은 강하지만 대규모 인덱스 저장, shard, retention, mapping 관리 부담이 큼 | 본문 인덱스 부담이 낮아 저장 비용이 유리함 |

도입 판단: ELK를 바로 대체하기보다는 로그 성격을 분리하는 방식이 현실적이다. 보안/감사/정밀 검색 로그는 기존 ELK/Wazuh/Kafka 경로에 두고, 서비스 운영자가 빠르게 장애 상황을 확인해야 하는 애플리케이션/컨테이너 로그는 Loki로 병행 수집하는 방식이 좋다. 특히 Prometheus에서 오류율 증가를 확인한 뒤 Grafana Explore에서 Loki 로그를 보고, 로그의 trace_id를 통해 Tempo trace로 넘어가는 흐름은 기존 ELK 중심 분석보다 훨씬 더 효율적으로 장애를 추적 및 대응할 수 있다. Kafka 기반 대량 로그 파이프라인은 유지하되, Grafana 중심 관측성 로그는 Promtail, Grafana Alloy, Fluent Bit 같은 경량 수집기로 별도 경로를 구성할 수 있다.

보안 로그 분석과 compliance 요구가 강한 로그는 Wazuh/ELK가 계속 주도하고, Loki는 운영 장애 분석용 보조 저장소로 시작하는 것이 안전하다.

## 3. 메트릭: Zabbix vs Prometheus

현재 팀에서는 Zabbix가 하드웨어와 시스템 메트릭 감시에 사용되고 있다. Zabbix는 서버, 네트워크 장비, SNMP, agent 기반 인프라 상태 감시에 강하고, NOC 관점의 임계치 알림과 장비 상태 관리에 익숙한 도구다. 반면 Prometheus는 애플리케이션과 Kubernetes 환경에서 label 기반 시계열 데이터를 수집하고 PromQL로 SLO, 오류율, latency를 계산하는 데 강하다.

| 비교 항목 | Zabbix | Prometheus |
| --- | --- | --- |
| 주요 목적 | 하드웨어, OS, 네트워크 장비, 시스템 availability 중심 모니터링 | 애플리케이션, 컨테이너, Kubernetes, exporter 기반 시계열 관측 |
| 수집 방식 | Agent, SNMP, trap 등 인프라 감시에 익숙한 방식 | Prometheus가 `/metrics` endpoint를 주기적으로 scrape하는 pull 방식 |
| 데이터 모델 | Host, item, trigger 중심으로 장비/시스템 상태를 관리 | metric name + label 조합의 time series 모델, PromQL로 집계/비율/분위수 계산 |
| 강점 | 장비 상태, 서버 자원, 전통적 임계치 알림, 운영팀 친화적 UI | 서비스별 request rate, error rate, p95 latency, Kafka lag, pod 상태 등 cloud-native 분석 |
| 팀 적용 관점 | 물리 장비, VM, OS, 네트워크, 기본 시스템 장애 감시는 Zabbix 유지 | MSA/Kubernetes 서비스 품질, SLO, 애플리케이션 지표, Grafana dashboard는 Prometheus 도입 적합 |

도입 판단: Zabbix는 인프라 상태 감시의 기준 시스템으로 유지하고, Prometheus는 애플리케이션과 Kubernetes 관측 지표를 보강하는 방향이 적절하다. 예를 들어 서버 CPU, 메모리, 디스크, 장비 장애는 Zabbix가 계속 담당하고, 서비스별 5xx 비율, API latency p95, pod restart, container resource, Kafka consumer lag 같은 운영 질문은 Prometheus와 Grafana로 다루면 역할이 분명해진다.

- Prometheus는 단순 서버 감시보다 "서비스가 사용자 관점에서 정상인가"를 계산하는 데 강하므로 SLO와 alert rule 설계가 함께 필요하다.
- Zabbix와 Prometheus를 같은 목적의 중복 도구로 보지 말고, 인프라 availability와 서비스 observability로 역할을 나누는 것이 좋다.
- 장기 보존이나 여러 Prometheus 인스턴스 통합이 필요하면 Mimir 같은 remote write backend를 함께 검토한다.

## 4. 트레이스: PinPoint vs Tempo + OTel Collector

현재 팀의 trace/APM 영역은 PinPoint를 사용 중이며 업그레이드 또는 고도화가 필요한 상태로 이해된다. PinPoint는 Java APM 완성도가 높고, Server Map, Scatter Chart, Call Stack, JVM Inspector를 한 UI에서 제공한다. 반면 OpenTelemetry Collector와 Tempo 조합은 특정 APM 제품보다 표준 기반 trace 파이프라인에 가깝고, 다양한 언어와 백엔드 선택을 허용한다.

| 비교 항목 | PinPoint | Trace + OTel Collector + Tempo |
| --- | --- | --- |
| 성격 | Agent, Collector, Storage, Web UI가 결합된 Java APM 완성형 플랫폼 | OpenTelemetry 표준 계측 + Collector 수집/처리 + Tempo 저장/Grafana 조회 구조 |
| 계측 | Java agent 중심, 코드 변경 없이 JVM 옵션으로 빠르게 붙이기 쉬움 | OTel SDK 또는 auto instrumentation, Java 외 Go, Node.js, Python, .NET 등 멀티언어에 유리 |
| 분석 화면 | Server Map, Scatter Chart, transaction call stack, JVM/GC/Thread 상태 분석에 강함 | Grafana에서 metrics, logs, traces를 연결하고 TraceQL, span metrics, service graph를 활용 |
| 확장성 | PinPoint 생태계와 저장소 구조에 묶이기 쉬움 | OTLP 기반으로 Tempo, Jaeger, Zipkin, Elastic, Datadog 등 여러 backend로 전송 가능 |
| 팀 적용 관점 | Java/Spring 레거시 서비스와 개발팀 중심 APM 분석은 PinPoint 유지/고도화 가치가 큼 | 멀티언어 MSA, Kubernetes, 벤더 중립 표준, 로그/메트릭 연계 분석은 OTel + Tempo 도입 적합 |

도입 판단: Java 서비스가 대부분이고 개발자가 call stack, DB query 시간, JVM 상태를 즉시 보아야 한다면 PinPoint 고도화가 여전히 유효하다. 하지만 서비스가 Java만이 아니거나, Kubernetes와 MSA에서 trace를 표준 데이터로 수집해 Grafana, Loki, Prometheus와 연결하려면 OpenTelemetry Collector와 Tempo를 병행 도입하는 것이 장기적으로 유리하다.

- PinPoint는 "이 요청이 어느 메서드, DB, 외부 API 호출에서 느렸는가"를 빠르게 보여주는 개발팀 APM에 강하다.
- OTel Collector는 batch, retry, queue, sampling, attribute 처리, multi-export를 통해 trace 파이프라인을 플랫폼화하기 좋다.
- 현실적인 전환은 PinPoint를 당장 제거하는 방식이 아니라, 신규 MSA 또는 멀티언어 서비스부터 OTel 계측을 표준화하고 Grafana/Tempo 분석 경험을 축적하는 방식이다.

## 5. 최종 평가: LGTM은 어떨 때 도입해야 할까?

LGTM은 Loki, Grafana, Tempo, Mimir를 중심으로 logs, metrics, traces를 한 화면에서 연결하려는 스택이다. 이번 프로젝트의 관점에서는 기존 ELK, Zabbix, PinPoint를 모두 대체하는 단일 해답이 아니라, cloud-native 서비스 운영에서 장애 원인 분석 흐름을 통합하는 보완/확장 플랫폼으로 평가하는 것이 적절하다.

| 판단 항목 | 평가 | 설명 |
| --- | --- | --- |
| 도입을 적극 검토할 상황 | Kubernetes/MSA 비중이 커지고, 서비스별 로그/메트릭/트레이스를 한 화면에서 연결해야 하는 경우 | Prometheus에서 에러율을 보고, Loki에서 관련 로그를 찾고, Tempo에서 downstream 병목을 확인하는 흐름이 필요 |
| 병행 도입이 적절한 상황 | ELK/Wazuh, Zabbix, PinPoint가 이미 운영 중이고 각자 역할이 명확한 경우 | 보안 로그는 ELK/Wazuh, 인프라는 Zabbix, Java APM은 PinPoint를 유지하면서 신규 MSA 관측성에 LGTM 적용 |
| 도입 우선순위가 낮은 상황 | 서비스가 단순하고 로그 전문 검색이나 장비 감시만으로 충분한 경우 | 운영팀이 OTel Collector, PromQL, LogQL, label 설계를 관리할 여력이 없으면 초기 부담이 커질 수 있음 |
| 성공 조건 | label/cardinality 정책, metric naming, trace sampling, retention, alert 기준을 사전에 정해야 함 | 도구 설치보다 운영 질문을 먼저 정의해야 dashboard와 alert가 실제 장애 대응에 쓰임 |

## 6. 최종 결론

LGTM은 "보안 로그 검색 시스템"이나 "하드웨어 감시 시스템"의 단순 대체재가 아니다. 팀의 현재 구조에서는 ELK/Wazuh는 보안/검색, Zabbix는 인프라 감시, PinPoint는 Java APM이라는 강점을 유지하되, Kubernetes와 MSA 서비스의 장애 분석 표준 경로로 LGTM을 도입하는 전략이 가장 현실적이다. 도입 우선순위는 신규 서비스, 트래픽 흐름이 복잡한 서비스, 장애 시 로그/메트릭/트레이스를 함께 봐야 하는 서비스부터 잡는 것이 좋다.
