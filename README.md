# Eureka Registrar Buildpack

This is a intermediate buildpack for Cloud Foundry that provides integration with the Spring Cloud Eureka 
server *for any programming language* supported by the platform, and requiring *zero application code 
changes*.

When this buildpack is present in your Cloud Foundry deployment, all you will have to do to register all 
instances of your application with the Eureka discovery server is bind the application to your Spring Cloud
Eureka Servive instance. Instances will then automatically be registered and continue to send heartbeats
as long as the application container is alive.
